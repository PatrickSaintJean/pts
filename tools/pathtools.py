import pickle

from aof.path import Path
import numpy as np
from aof.common import vector_angle
import aof.func as func
import scipy as sp

class PathTools:
    """
    Implements operations on reaction pathways, such as estimation of 
    transition states using gradient/energy information.

    >>> pt = PathTools([0,1,2,3], [1,2,3,2])
    >>> pt.steps
    array([ 0.,  1.,  2.,  3.])

    >>> pt.ts_highest()
    [(3, array([2]), 2.0, 2.0)]

    >>> pt = PathTools([0,1,2,3], [1,2,3,2], [0,1,-0.1,0])
    >>> res1 = pt.ts_splcub()

    >>> pt = PathTools([[0,0],[1,0],[2,0],[3.,0]], [1,2,3,2.], [[0,0],[1,0],[-0.1,0],[0,0]])
    >>> res2 = pt.ts_splcub()
    >>> res1[0][0] == res2[0][0]
    True

    >>> np.round(res1[0][0], 0)
    3.0
    >>> res1[0][0] > 3
    True

    Tests on path generated from a parabola.

    >>> xs = (np.arange(10) - 5) / 2.0
    >>> f = lambda x: -x*x
    >>> g = lambda x: -2*x
    >>> ys = f(xs)
    >>> gs = g(xs)
    >>> pt = PathTools(xs, ys, gs)
    >>> energy, pos, _, _ = pt.ts_splcub()[0]
    >>> np.round(energy) == 0
    True
    >>> (np.round(pos) == 0).all()
    True
    >>> type(str(pt))
    <type 'str'>


    Tests on path generated from a parabola, again, but shifted.

    >>> xs = (np.arange(10) - 5.2) / 2.0
    >>> f = lambda x: -x*x
    >>> g = lambda x: -2*x
    >>> ys = f(xs)
    >>> gs = g(xs)
    >>> pt = PathTools(xs, ys, gs)
    >>> energy, pos, _, _ = pt.ts_splcub()[0]
    >>> np.round(energy) == 0
    True
    >>> (np.round(pos) == 0).all()
    True

    >>> pt = PathTools([0,1,2,3,4], [1,2,3,2,1])
    >>> e, p, s0, s1 = pt.ts_spl()[0]
    >>> np.round([e,p])
    array([ 3.,  2.])

    >>> pt = PathTools([0,1,2,3,4], [1,2,3,2,1], [0,1,-0.1,0,1])
    >>> pt.ts_spl()[0] == (e, p, s0, s1)
    True



    """
    def __init__(self, state, energies, gradients=None):

        self.n = len(energies)
        self.state = np.array(state).reshape(self.n, -1)
        self.energies = np.array(energies)

        if gradients != None:
            self.gradients = np.array(gradients).reshape(self.n, -1)
            assert self.state.shape == self.gradients.shape

        assert len(state) == len(energies)

        self.steps = np.zeros(self.n)

        for i in range(self.n)[1:]:
            x = self.state[i]
            x_ = self.state[i-1]
            self.steps[i] = np.linalg.norm(x -x_) + self.steps[i-1]
        self.steps = self.steps# / self.steps[-1]

        # string for __str__ to print
        self.s = []

        # build fresh functional representation of optimisation 
        # coordinates as a function of a path parameter s
        self.xs = Path(self.state, self.steps)

        # Check to see whether spline path is comparable to Pythagorean one.
        # TODO: ideally, self.steps should be updated so that it's self 
        # consistent with the steps generated by the Path object, but at 
        # present, calculation of string length is too slow, so it's only done 
        # once and a simple comaprison is made.
        diff = lambda a,b:np.abs(a-b)
        arc = func.Integral(self.xs.tangent_length)
        l = np.array([arc(x) for x in self.xs.xs])
        self.s.append("Path length: %s" % l[-1])
        err = l - self.steps
        err = [diff(err[i], err[i-1]) for i in range(len(err))[1:]]
        self.s.append("Difference between Pythag v.s. spline positions: %s" % np.array(err).round(4))
        
 
    def __str__(self):
        return '\n'.join(self.s)

    def ts_spl(self, tol=1e-10):
        """Returns list of all transition state(s) that appear to exist along
        the reaction pathway."""

        n = self.n
        Es = self.energies.reshape(-1,1)
        ss = self.steps.copy()

        ys = self.state.copy()

        E = Path(Es, ss)

        ts_list = []
        for i in range(n)[1:]:
            s0 = ss[i-1]
            s1 = ss[i]
            dEds_0 = E.fprime(s0)
            dEds_1 = E.fprime(s1)

            if dEds_0 > 0 and dEds_1 < 0:
                #print "ts_spl: TS in %f %f" % (s0,s1)
                f = lambda x: np.atleast_1d(E.fprime(x)**2)[0]
                assert s0 < s1, "%f %f" % (s0, s1)
                s_ts, fval, ierr, numfunc = sp.optimize.fminbound(f, s0, s1, full_output=1)

                # FIXME: a bit dodgy
                assert fval < 0.001
                ts_e = E(s_ts)
                assert ts_e.size == 1
                ts_e = ts_e[0]
                ts = self.xs(s_ts)
                ts_list.append((ts_e, ts, s0, s1, i-1, i))

        ts_list.sort()
        return ts_list

    def ts_splavg(self, tol=1e-10):
        """
        Uses a spline representation of the molecular coordinates and 
        a cubic polynomial defined from the slope / value of the energy 
        for pairs of points along the path.
        """

        ys = self.state.copy()
        ss = self.steps
        Es = self.energies
        self.s.append("Es: %s" % Es)

        self.plot_str = ""
        for s, e in zip(ss, Es):
            self.plot_str += "%f\t%f\n" % (s, e)

       
        ts_list = []

        for i in range(self.n)[1:]:#-1]:
            # For each pair of points along the path, find the minimum
            # energy and check that the gradient is also zero.
            E_0 = Es[i-1]
            E_1 = Es[i]

            s0 = ss[i-1]
            s1 = ss[i]
            
            dEdx_0 = self.gradients[i-1]
            dEdx_1 = self.gradients[i]
            dxds_0 = self.xs.fprime(ss[i-1])
            dxds_1 = self.xs.fprime(ss[i])

            #energy gradient at "left/right" bead along path
            dEds_0 = np.dot(dEdx_0, dxds_0)
            dEds_1 = np.dot(dEdx_1, dxds_1)

            dEdss = np.array([dEds_0, dEds_1])

            self.s.append("E_1 %s" % E_1)
            if (E_1 >= E_0 and dEds_1 <= 0) or (E_1 <= E_0 and dEds_0 > 0):
                #print "ts_splcub_avg: TS in %f %f" % (ss[i-1],ss[i])

                E_ts = (E_1 + E_0) / 2
                s_ts = (s1 + s0) / 2
                ts_list.append((E_ts, self.xs(s_ts), s0, s1, i-1, i))

        return ts_list


    def ts_splcub(self, tol=1e-10):
        """
        Uses a spline representation of the molecular coordinates and 
        a cubic polynomial defined from the slope / value of the energy 
        for pairs of points along the path.
        """

        ys = self.state.copy()

        ss = self.steps
        Es = self.energies
        self.s.append("Es: %s" % Es)

        self.plot_str = ""
        for s, e in zip(ss, Es):
            self.plot_str += "%f\t%f\n" % (s, e)

        # build fresh functional representation of optimisation 
        # coordinates as a function of a path parameter s

        
        ts_list = []

        for i in range(self.n)[1:]:#-1]:
            # For each pair of points along the path, find the minimum
            # energy and check that the gradient is also zero.
            E_0 = Es[i-1]
            E_1 = Es[i]
            dEdx_0 = self.gradients[i-1]
            dEdx_1 = self.gradients[i]
            dxds_0 = self.xs.fprime(ss[i-1])
            dxds_1 = self.xs.fprime(ss[i])

            # energy gradient at "left/right" bead along path
            dEds_0 = np.dot(dEdx_0, dxds_0)
            dEds_1 = np.dot(dEdx_1, dxds_1)



            dEdss = np.array([dEds_0, dEds_1])

            self.s.append("E_1 %s" % E_1)
            if (E_1 >= E_0 and dEds_1 <= 0) or (E_1 <= E_0 and dEds_0 > 0):
                #print "ts_splcub: TS in %f %f" % (ss[i-1],ss[i])
                self.s.append("Found: i = %d E_1 = %f E_0 = %f dEds_1 = %f dEds_0 = %f" % (i, E_1, E_0, dEds_1, dEds_0))

                cub = func.CubicFunc(ss[i-1:i+1], Es[i-1:i+1], dEdss)
#                print ss[i-2:i+1], Es[i-2:i+1]
#                print ss, Es
#                print i
#                if i < 2:
#                    continue
#                cub = func.QuadFunc(ss[i-2:i+1], Es[i-2:i+1])
#                print ss[i], cub(ss[i]), Es[i]
                self.s.append("ss[i-1:i+1]: %s" % ss[i-1:i+1])

                self.s.append("cub: %s" % cub)

                # find the stationary points of the cubic
                statpts = cub.stat_points()
                self.s.append("statpts: %s" % statpts)
                assert statpts != []
                found = 0
                for p in statpts:
                    # test curvature
                    if cub.fprimeprime(p) < 0:
                        ts_list.append((cub(p), self.xs(p), ss[i-1], ss[i], i-1, i))
                        found += 1

#                assert found == 1, "Must be exactly 1 stationary points in cubic path segment but there were %d" % found

                self.plot_str += "\n\n%f\t%f\n" % (p, cub(p))

        return ts_list

    def ts_highest(self):
        """
        Just picks the highest energy from along the path.
        """
        i = self.energies.argmax()
        ts_list = [(self.energies[i], self.state[i], self.steps[i], self.steps[i], i, i)]

        return ts_list


def pickle_path(mi, CoS, file):
    a,b,c = CoS.path_tuple()
    cs = mi.build_coord_sys(a[0])
    f = open(file, 'wb')
    pickle.dump((a,b,c,cs), f)
    f.close()


# Testing the examples in __doc__strings, execute
# "python gxmatrix.py", eventualy with "-v" option appended:
if __name__ == "__main__":
    import doctest
    doctest.testmod()

# You need to add "set modeline" and eventually "set modelines=5"
# to your ~/.vimrc for this to take effect.
# Dont (accidentally) delete these lines! Unless you do it intentionally ...
# Default options for vim:sw=4:expandtab:smarttab:autoindent:syntax


