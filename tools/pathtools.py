from __future__ import with_statement
__doc__ = \
"""
Contains code to analyse the path and generate TS guesses via interpolation.

Not intended to be run on its own, but

    $ python pathtools.py

will run the doctests.

"""

import sys
import pickle
import os
import logging


from pts.path import Path, Arc
import numpy as np
from pts.common import vector_angle
import pts.func as func
import scipy as sp
from pts.threepointmin import ts_3p_gr
from pts.io.read_inputs import get_transformation
from pts.io.cmdline import get_mask
from pts.cfunc import Justcarts, Masked
from numpy import loadtxt

lg = logging.getLogger("pts.tools")
lg.setLevel(logging.INFO)

class PathTools:
    """
    Implements operations on reaction pathways, such as estimation of 
    transition states using gradient/energy information.

    >>> pt = PathTools([0,1,2,3], [1,2,3,2])
    >>> pt.steps
    array([ 0.,  1.,  2.,  3.])

    >>> pt.ts_highest()
    [(3, array([2]), 2.0, 2.0, 2.0, 2, 2)]

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
    >>> energy, pos, _, _, _, _, _ = pt.ts_splcub()[0]
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
    >>> energy, pos, _, _, _, _, _ = pt.ts_splcub()[0]
    >>> np.round(energy) == 0
    True
    >>> (np.round(pos) == 0).all()
    True

    >>> pt = PathTools([0,1,2,3,4], [1,2,3,2,1])
    >>> e, p, s0, s1, s_ts, i_, i = pt.ts_spl()[0]
    >>> np.round([e,p])
    array([ 3.,  2.])

    >>> pt = PathTools([0,1,2,3,4], [1,2,3,2,1], [0,1,-0.1,0,1])
    >>> pt.ts_spl()[0] == (e, p, s0, s1, s_ts, i_, i)
    True

    >>> pt = PathTools([0,1,2,3,4], [1,2,3,2,1])
    >>> e = pt.ts_bell()[0]
    >>> np.round(np.array(e), 2)
    array([ 3.,  2.,  1.,  2.,  2.,  1.,  2.])

    >>> pt = PathTools([0,1,2,3,4,5], [1,3,5,5,3,1])
    >>> e = pt.ts_bell()[0]
    >>> np.round(np.array(e), 2)
    array([ 5.3,  2.5,  2. ,  3. ,  2.5,  2. ,  3. ])

    >>> pt = PathTools([0,1,2,5,6], [1,3,5,3,1])
    >>> e = pt.ts_bell()[0]
    >>> np.round(np.array(e), 2)
    array([ 5.54,  2.83,  2.  ,  5.  ,  2.83,  2.  ,  3.  ])


    """
    def __init__(self, state, energies, gradients=None, steps = None):

        # string for __str__ to print
        self.s = []

        self.n = len(energies)
        self.s.append("Beads: %d" % self.n)
        self.state = np.array(state).reshape(self.n, -1)
        self.energies = np.array(energies)

        if gradients != None:
            self.gradients = np.array(gradients).reshape(self.n, -1)
            assert self.state.shape == self.gradients.shape

        assert len(state) == len(energies)

        # cartesian distances along path
        self.cart_lengths = np.zeros(self.n)
        x = self.state[1]
        x_ = self.state[0]
        for i in range(self.n)[1:]:
            x = self.state[i]
            x_ = self.state[i-1]
            self.cart_lengths[i] = np.linalg.norm(x -x_) + self.cart_lengths[i-1]

        if steps == None:
            self.steps = self.cart_lengths.copy()
        else:
            assert len(steps) == self.n
            self.steps = steps.copy()

        # set up array of tangents, not based on a spline representation of the path
        self.non_spl_grads = []
        x = self.state[1]
        x_ = self.state[0]
        l = np.linalg.norm(x - x_)
        self.non_spl_grads.append((x - x_) / l)
        for i in range(self.n)[1:]:
            x = self.state[i]
            x_ = self.state[i-1]
            l = np.linalg.norm(x - x_)
            self.non_spl_grads.append((x - x_) / l)

        self.non_spl_grads = np.array(self.non_spl_grads)
        assert len(self.non_spl_grads) == self.n, "%d != %d" % (len(self.non_spl_grads), self.n)


        # build fresh functional representation of optimisation 
        # coordinates as a function of a path parameter s
        self.xs = Path(self.state, self.steps)

        # Check to see whether spline path length is comparable to Pythagorean one.
        # TODO: ideally, self.steps should be updated so that it's self 
        # consistent with the steps generated by the Path object, but at 
        # present, calculation of string length is too slow, so it's only done 
        # once and a simple comaprison is made.
        diff = lambda a,b:np.abs(a-b)

        # arc(t) computes the length of the path xs(t) from t=0:
        arc = Arc(self.xs)
        self.lengths = np.array([arc(x) for x in self.steps])
#        print "self.lengths", self.lengths
#        print "self.cart_lengths", self.cart_lengths
        self.s.append("Path length: %s" % self.lengths[-1])
        err = self.lengths - self.steps
        err = [diff(err[i], err[i-1]) for i in range(1, len(err))] # why have I redefined err like this?
        self.s.append("Difference between Pythag v.s. spline positions: %s" % np.array(err).round(4))

        # There have been some problems with the calculation of the slope along the path
        # This calculates it via an alternate method
        self.para_forces_fd = []
        self.use_energy_based_dEds_calc = False
        if self.use_energy_based_dEds_calc:
            ss = self.steps
            Es = self.energies
            self.dEds_all = np.zeros(self.n)
            for i in range(self.n):
                if i == 0:
                    tmp = (Es[i+1] - Es[i]) / np.linalg.norm(ss[i+1] - ss[i])
                elif i == self.n - 1:
                    tmp = (Es[i] - Es[i-1]) / np.linalg.norm(ss[i] - ss[i-1])
                else:
                    tmp = (Es[i+1] - Es[i-1]) / np.linalg.norm(ss[i+1] - ss[i-1])
                self.para_forces_fd.append(tmp)
                self.dEds_all[i] = tmp

    def __str__(self):
        return '\n'.join(self.s)

    def projections(self):

        for i in range(self.n):
            dEdx = self.gradients[i]
            t = self.xs.fprime(self.steps[i])
            t = t / np.linalg.norm(t)

            along_path = np.dot(dEdx, t) * t
            across_path = dEdx - along_path

            yield along_path, across_path
       
    def modeandcurvature(self, s0, leftbd, rightbd, trafo):
        """The mode along the path in the point s0 and
        the curvature for it are given back in several
        possible approximations
        """
        if leftbd == rightbd:
            leftbd -= 1
            rightbd += 1

        if leftbd < 0:
             leftbd = 0
        if rightbd > (len(self.state)-1):
             rightbd = len(self.state) -1

        leftcoord = trafo(self.state[leftbd])
        rightcoord = trafo(self.state[leftbd])

        modedirect = rightcoord - leftcoord
        normer = np.sqrt(sum(sum(modedirect * modedirect)))
        modedirect /= normer

        modeint = self.state[rightbd] - self.state[leftbd]
        normer = np.sqrt(sum(modeint * modeint))
        modeint /= normer
        modeint = np.asarray(modeint)
        transfer = trafo.fprime(self.xs(s0)).flatten()
        transfer.shape = (modeint.shape[0], -1)
        modefromint = np.dot( modeint, transfer)

        modeint = self.state[-1] - self.state[0]
        normer = np.sqrt(sum(modeint * modeint))
        modeint /= normer
        modeint = np.asarray(modeint)
        transfer = trafo.fprime(self.xs(s0)).flatten()
        transfer.shape = (modeint.shape[0], -1)
        modeallpath = np.dot(modeint, transfer)

        modeint = self.xs.fprime(s0)
        normer = np.sqrt(sum(modeint * modeint))
        modeint /= normer
        modepath = np.dot(np.asarray(modeint), transfer)

        modefromint = np.reshape(modefromint, np.shape(modedirect))
        modepath = np.reshape(modepath, np.shape(modedirect))
        modeallpath = np.reshape(modeallpath, np.shape(modedirect))

        return ("first to last bead", modeallpath),  ("directinternal", modefromint), ("frompath", modepath)


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
#            print "dEds_0, dEds_1 %f, %f" % (dEds_0, dEds_1)

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
                ts_list.append((ts_e, ts, s0, s1, s_ts, i-1, i))

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
        self.s.append("Begin ts_splavg()")
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

            if self.use_energy_based_dEds_calc:
                dEds_0 = self.dEds_all[i-1]
                dEds_1 = self.dEds_all[i]

            dEdss = np.array([dEds_0, dEds_1])

            self.s.append("E_1 %s" % E_1)
            if (E_1 >= E_0 and dEds_1 <= 0) or (E_1 <= E_0 and dEds_0 > 0):
                #print "ts_splcub_avg: TS in %f %f" % (ss[i-1],ss[i])

                E_ts = (E_1 + E_0) / 2
                s_ts = (s1 + s0) / 2
                ts_list.append((E_ts, self.xs(s_ts), s0, s1, s_ts, i-1, i))

        ts_list.sort()
        return ts_list


    def ts_bell(self):
        ys = self.state.copy()

        ss = self.steps
        Es = self.energies
        E = Path(Es, ss)

        samples = np.arange(0, 1, 0.001) * ss[-1]
        E_points = np.array([E(p) for p in samples])
        assert (np.array([E(p) for p in ss]) - Es).round().sum() == 0, "%s\n%s" % ([E(p) for p in ss], Es)

        sTS = samples[E_points.argmax()]
        yTS = self.xs(sTS)

        l = []
        for i in range(len(ss))[1:]:
            if ss[i-1] < sTS <= ss[i]:
                sL = ss[i-1]
                sR = ss[i]
                yR = ys[i]
                yL = ys[i-1]
                if sTS - sL < sR - sTS:
                    yTS = yL + (sTS - sL) / (sR - sL) * (yR - yL)
                else:
                    yTS = yR + (sTS - sR) / (sR - sL) * (yR - yL)
                l.append((E_points.max(), yTS, sL, sR, sTS, i-1, i))
                break

        return l

    def ts_splcub(self, tol=1e-10):
        """
        Uses a spline representation of the molecular coordinates and 
        a cubic polynomial defined from the slope / value of the energy 
        for pairs of points along the path.
        """

        ys = self.state.copy()

        ss = self.steps
        Es = self.energies
        self.s.append("Begin ts_splcub()")

        self.s.append("Es: %s" % Es)

        self.plot_str = ""
        for s, e in zip(ss, Es):
            self.plot_str += "%f\t%f\n" % (s, e)

        # build fresh functional representation of optimisation 
        # coordinates as a function of a path parameter s

        
        ts_list = []

        self.para_forces = []

              
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
            
            # debugging
            dEds_0_ = np.dot(dEdx_0, self.non_spl_grads[i-1])
            dEds_1_ = np.dot(dEdx_1, self.non_spl_grads[i])

            self.para_forces.append(dEds_1)

            if self.use_energy_based_dEds_calc:
                dEds_0 = self.dEds_all[i-1]
                dEds_1 = self.dEds_all[i]
            dEdss = np.array([dEds_0, dEds_1])

            lg.debug("dEdss(%d) = %s" % (i, dEdss))

            self.s.append("E_1 %s" % E_1)
            self.s.append("Checking: i = %d E_1 = %f E_0 = %f dEds_1 = %f dEds_0 = %f" % (i, E_1, E_0, dEds_1, dEds_0))
            self.s.append("Non-spline dEds_1 = %f dEds_0 = %f" % (dEds_1_, dEds_0_))

            if (E_1 >= E_0 and dEds_1 <= 0) or (E_1 <= E_0 and dEds_0 > 0):
                #print "ts_splcub: TS in %f %f" % (ss[i-1],ss[i])
                self.s.append("Found")

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
                        ts_list.append((cub(p), self.xs(p), ss[i-1], ss[i], p, i-1, i))
                        found += 1

#                assert found == 1, "Must be exactly 1 stationary points in cubic path segment but there were %d" % found

                self.plot_str += "\n\n%f\t%f\n" % (p, cub(p))

        ts_list.sort()
        return ts_list

    def ts_highest(self):
        """
        Just picks the highest energy from along the path.
        """
        i = self.energies.argmax()
        ts_list = [(self.energies[i], self.state[i], self.steps[i], self.steps[i], self.steps[i], i, i)]

        return ts_list

    def ts_threepoints(self, withmove = False):
        """Uses the threepointmin module to get an approximation just
        from the three points supposed to be next nearest to the transition state

        if withmove = True, calculates also the approximation with the beads
        one to the left and ones to the right of the hightest bead
        """

        i = self.energies.argmax()

        # Guard against situation when TS is too close to the ends for the code to work
        if i < 2 or i > len(self.energies) - 2:
            return []

        ts_list = []
        if withmove:
             xts, gts, ets, gpr1, gpr2, work =  ts_3p_gr(self.state[i-2], self.state[i-1], self.state[i], self.gradients[i-2], self.gradients[i-1], self.gradients[i], self.energies[i-2], self.energies[i-1], self.energies[i])
             ts_list.append((ets, xts, self.steps[i-1], self.steps[i+1],self.steps[i], i-1, i+1))
             xts, gts, ets, gpr1, gpr2, work =  ts_3p_gr(self.state[i], self.state[i+1], self.state[i+2], self.gradients[i], self.gradients[i+1], self.gradients[i+2], self.energies[i], self.energies[i+1], self.energies[i+2])
             ts_list.append((ets, xts, self.steps[i-1], self.steps[i+1],self.steps[i], i-1, i+1))

        xts, gts, ets, gpr1, gpr2, work =  ts_3p_gr(self.state[i-1], self.state[i], self.state[i+1], self.gradients[i-1], self.gradients[i], self.gradients[i+1], self.energies[i-1], self.energies[i], self.energies[i+1])
        if not work:
            print "WARNING: this transition state approximation is rather far away from the initial path"
            print "Please verify that it makes sense before using it"
        ts_list.append((ets, xts, self.steps[i-1], self.steps[i+1],self.steps[i], i-1, i+1))

        return ts_list

from copy import deepcopy, copy
from pickle import load, dump

def pickle_path(file,
                geometries, energies, gradients,
                tangents, abscissas,
                symbols, trafo):
    """
    Original format: a nested tuple in the file:

    v1:

    ((geometries, abscissas, energies, gradients), (symbols, trafo))

    v2:

    (geometries, energies, gradients, tangents, abscissas), (symbols, trafo))
    """

    path = geometries, energies, gradients, tangents, abscissas
    system = symbols, trafo

    with open(file, "wb") as f:
        dump((path, system), f, protocol=2)

def unpickle_path(file):
    """
    Original format: a nested tuple in the file:

    v1:

    ((geometries, abscissas, energies, gradients), (symbols, trafo))

    v2:

    (geometries, energies, gradients, tangents, abscissas), (symbols, trafo))
    """

    with open(file, "r") as f:
        contents = load(f)

    path, system = contents

    # this hack  is for backwards  compatibility, remove when  no more
    # necessary:
    try:
        # older versions had only two items in the file:
        geometries, abscissas, energies, gradients = path

        print >> sys.stderr, "WARNING: old file format:", file
        tangents = None

    except ValueError, e:
        assert e.message == "too many values to unpack"

        # newer versions have tangent info too:
        geometries, energies, gradients, tangents, abscissas = path

    symbols, trafo = system

    return geometries, energies, gradients, tangents, abscissas, symbols, trafo

def read_path_fix(symbfile, zmatifiles = None, maskfile = None, maskedgeo = None):
    """
    If not stored in a pickle.path it does not makes too much sense to give
    unchangeable things for every geoemtry, thus separate them

    Here the symbols (define the system) are read in, the function to tranform into cartesian
    is also generated, uses zmat files to build the same system as before, if the coordinates
    are with a mask, here is the possibility to set this also
    """
    # loadtxt (and especially savetxt) do not seems to like strings
    f = open(symbfile, "r")
    sr = f.read()
    f.close()
    symbols = sr.split()


    if len(zmatifiles)==0:
        trafo = Justcarts()
    else:
        trafo, __, __, __ = get_transformation(zmatifiles, len(symbols))

    if maskfile is not None:
        assert (maskedgeo is not None)
        f = open(maskfile, "r")
        sr = f.read()
        f.close()
        mask = get_mask(sr)
        geo_raw = loadtxt(maskedgeo)
        trafo = Masked(trafo, mask, geo_raw)

    return symbols, trafo

def read_path_coords(coordfile, pathpsfile = None, energyfile = None, forcefile = None):
    """
    If not stored in a pickle.path it does not makes too much sense to give
    unchangeable things for every geoemtry, thus separate them

    Here a the things which change with every iteration, pathps (abscissa) are only
    there if it has been a string calculation
    energies and forces are not needed every time and will propably not provided then
    """

    coord = loadtxt(coordfile)

    if pathpsfile == None:
        pathps = None
    else:
        pathps = loadtxt(pathpsfile)

    if energyfile == None:
        energy = None
    else:
        energy = loadtxt(energyfile)

    if forcefile == None:
        force = None
    else:
        force = loadtxt(forcefile)

    return coord, pathps, energy, force

plot_s = \
"""
plot "%(fn)s", "%(fn)s" smooth cspline
"""
splot_s = \
"""
#set pm3d
set hidden
set xlabel "Iterations"
set ylabel "Reaction Coordinate"
splot "%(fn_paths)s" with lines, "%(fn_tss)s" lw 8
"""

def gnuplot_path(pathtools, filename):

    es = pathtools.energies
    N = len(es)
    p = pathtools.xs
    state = pathtools.state
    lengths = pathtools.lengths

    #arc = func.Integral(p.tangent_length)
    #l = np.array([arc(x) for x in np.arange(N)])
    #print "l", l

    s = ['%f\t%f' % (lengths[i], es[i]) for i in range(N)]
    s = '\n'.join(s)

    f = open(filename + '.data', 'w')
    f.write(s)
    f.close()

    f = open(filename + '.gp', 'w')
    d = {'fn': filename + '.data'}
    f.write(plot_s % d)
    f.close()
    os.system('gnuplot -persist ' + filename + '.gp')

def gnuplot_path3D(arc_list, ts_list, filename):

    f = open(filename + '.paths.data', 'w')
    prev_beads = -1
    for entry in arc_list:
        i, _, es, _, ss = entry
        beads = len(ss)

        s = ['%d\t%f\t%f' % (i, s, e) for (s,e) in zip(ss,es)]
        s = '\n'.join(s) + '\n'

        if beads != prev_beads and prev_beads != -1:
            # write out extra newline. Required by gnuplot, which cannot plot
            # continuous surfaces if there are not the same number of data
            # points in each series.
            f.write('\n')
        prev_beads = beads

        f.write(s)
        f.write('\n')

    f.close()

    f = open(filename + '.tss.data', 'w')
    for entry in ts_list:
        i, s, e = entry

        s = '%d\t%f\t%f\n' % (i, s, e)

        f.write(s)

    f.close()

    f = open(filename + '.gp', 'w')
    d = {'fn_paths': filename + '.paths.data', 'fn_tss': filename + '.tss.data'}
    f.write(splot_s % d)
    f.close()
    os.system('gnuplot ' + filename + '.gp' + ' -')

        
    

# Testing the examples in __doc__strings, execute
# "python gxmatrix.py", eventualy with "-v" option appended:
if __name__ == "__main__":
    print "Running doctests"
    import doctest
    doctest.testmod()

    print __doc__

# You need to add "set modeline" and eventually "set modelines=5"
# to your ~/.vimrc for this to take effect.
# Dont (accidentally) delete these lines! Unless you do it intentionally ...
# Default options for vim:sw=4:expandtab:smarttab:autoindent:syntax
