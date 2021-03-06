#!/usr/bin/env python
from __future__ import print_function
__doc__ = \
"""
Runge-Kutta procedures adapted from cosopt/quadratic_string.py

Example: Integrate

    dy / dt = f(t, y)

given below from (t0, y0) to t = T (or infinity)

    >>> def f(t, y):
    ...     yp = - (y - 100.0)
    ...     yp[0] *= 0.01
    ...     yp[1] *= 100.
    ...     return yp

    >>> t0 = 0.0
    >>> y0 = [80., 120]

    >>> y = ODE(t0, y0, f)

    >>> y(0.125)
    array([  80.02498438,  100.00007444])

    >>> y.fprime(0.125) - f(0.125, y(0.125))
    array([ 0.,  0.])

    >>> limit(y)
    array([ 100.,  100.])

FIXME:  The "exact"  integration using  scipy.integrate.odeint without
tolerance  settings may  require  unnecessary much  time.  Is there  a
better way?
"""

__all__ = ["ODE", "limit", "rk45", "rk4", "rk5"]

from numpy import array, max, abs, searchsorted, zeros, shape
from scipy.integrate import odeint
from func import Func

VERBOSE = False

TOL = 1.0e-7

def limit(y, t0=0.0, tol=TOL, maxit=12):
    """
    Compute  the limit  of  y(t) at  t  = inf.  The  function y(t)  is
    supposed to be defined at least in the interval [t0, inf).

    Example:

        >>> from numpy import exp
        >>> def f(t):
        ...     return 100.0 * ( 1. - exp(-t))

        >>> limit(f)
        100.0
    """

    # integrate  to infinity,  for  that guess  the upper  integration
    # limit:
    t1 = t0 + 1.0

    # will be comparing these two:
    y1, y2 = y(t0), y(t1)

    iteration = -1
    while max(abs(y2 - y1)) > tol and iteration < maxit:
        iteration += 1

        # advance  the upper  limit, by  scaling the  difference  by a
        # factor:
        t0, t1 = t1, t1 + 2.0 * (t1 - t0)
        y1, y2 = y2, y(t1)

    if iteration >= maxit:
        print ("limit: WARNING: maxit=", maxit, "exceeded")

    if VERBOSE:
        print ("limit: t=", t1, "guessed", iteration, "times")

    return y2

class ODE(Func):
    def __init__(self, t0, y0, f, args=()):
        """Build a Func() y(t) by integrating

            dy / dt = f(t, y, *args)

        from t0 to t.

        It is supposed to work for any shape of y.

        Example:

            >>> def f(t, y):
            ...     yp = - (y - 100.0)
            ...     yp[0, 0] *= 0.01
            ...     yp[0, 1] *= 100.
            ...     yp[1, 0] *= 0.1
            ...     yp[1, 1] *= 1.0
            ...     return yp

            >>> t0 = 0.0
            >>> y0 = [[80., 120], [20.0, 200.]]

            >>> y = ODE(t0, y0, f)

            >>> y(0.0)
            array([[  80.,  120.],
                   [  20.,  200.]])

            >>> y(1.0)
            array([[  80.19900333,   99.99999999],
                   [  27.61300655,  136.78795028]])

        At large t all elements approach 100.0:

            >>> max(abs(y(10000.0) - 100.0)) < 1.0e-9
            True

            >>> max(abs(y.fprime(2.0) - f(2.0, y(2.0)))) == 0.0
            True

        Something is fishy with  integration into negative half. ODE()
        tries to avoid relying on odeint() with non-increasing list of
        arguments:

            >>> dt = 1.0e-2
            >>> z = ODE(t0 - dt, y(t0 - dt), f)
            >>> z(t0)
            array([[  80.        ,  120.00000447],
                   [  20.        ,  200.        ]])
        """

        # make a copy of the input (paranoya):
        y0 = array(y0)

        # table of known results:
        self.__ts = [t0]
        self.__ys = {t0 : y0}

        self.__yshape = y0.shape
        self.__ysize = y0.size

        # odeint() from scipy expects f(y, t) and flat array y:
        def fp(y, t):

            # call original function, restore original shape:
            yp = f(t, y.reshape(self.__yshape), *args)

            return yp.reshape(-1)

        def fm(y, t):

            # call original function, restore original shape:
            yp = -f(-t, y.reshape(self.__yshape), *args)

            return yp.reshape(-1)

        # this 1D-array valued function will be integrated:
        self.__fp = fp
        self.__fm = fm

    def f(self, t):

        # aliases:
        ts = self.__ts
        ys = self.__ys
        fp = self.__fp
        fm = self.__fm

        # return cached value, if possible (ys is a dict):
        if t in ys:
            return ys[t].copy()

        i = searchsorted(ts, t)

        # FIXME: t >= t0:
        # assert i > 0

        if i > 0:
            # integrate from t0 < t:
            t0 = ts[i-1]
            y0 = ys[t0]
        else:
            t0 = ts[i]
            y0 = ys[t0]

        # reshape temporarily:
        y0.shape = self.__ysize

        #
        # compute y(t), odeint() seems to be confused when t0 > t:
        #
        if t >= t0:
            assert t > t0
            _y0, y = odeint(fp, y0, [t0, t])
        else:
            assert t < t0
            _y0, y = odeint(fm, y0, [t0, -t])

        # restore original shape:
        y0.shape = self.__yshape
        y.shape = self.__yshape

        # insert new result into table:
        ts.insert(i, t)
        ys[t] = y

        if VERBOSE:
            print ("ODE: ts=", ts)
            print ("ODE: ys=", ys)

        return y.copy()

    def fprime(self, t):

        y = self.f(t)

        yp = self.__fp(y.reshape(-1), t)

        return yp.reshape(self.__yshape)

from numpy import sqrt, dot, inf

class Radius(Func):
    """
    For a Func  y(t) a Radius(y) is a Func, R(t),  defined as a length
    of the vector:

        R(t) = |y(t) - y(0)|

    if R = Radius(y).
    """

    def __init__(self, y):
        self.Y = y

    def taylor(self, t):
        y, yprime = self.Y.taylor(t)

        dy = y - self.Y(0.0)

        r = sqrt(dot(dy, dy))

        if r == 0.0:
            rprime = sqrt(dot(yprime, yprime))
        else:
            rprime = dot(dy, yprime) / r

        return r, rprime

class Clip(Func):
    """
    A Func Y = Clip(y) is a function, Y(R), of a radius, R, that finds
    and returns a y(t) <= R.

        >>> def f(t, y):
        ...     yp = - (y - 100.0)
        ...     yp[0] *= 0.01
        ...     yp[1] *= 100.
        ...     return yp

        >>> t0 = 0.0
        >>> y0 = [80., 120]
        >>> y = ODE(t0, y0, f)

    Instead of  a funciton  of time, y(t),  make a function,  Y(R), of
    radius R:

        >>> Y = Clip(y)

    This, in effect, integrates dy/dt = f(t, y) as long as |y - y0| <=
    R. This is how norm is defined here:

        >>> norm = lambda x: sqrt(dot(x, x))

    Note the norm of the change, Y(R) - Y(0), is equal to the argument
    R:

        >>> rs = [0.0, 1.0, 10., 20.0]
        >>> [abs(R - norm(Y(R) - Y(0.0))) < 1.0e-13 for R in rs]
        [True, True, True, True]

    If  the y(t)  has  a limit,  then  Y(R) becomes  constant at  some
    (trust) radius:

        >>> limit(y)
        array([ 100.,  100.])

        >>> Y(28.0)
        array([  99.59591794,  100.        ])

        >>> Y(29.0)
        array([ 100.,  100.])

        >>> Y(30.0)
        array([ 100.,  100.])
    """

    def __init__(self, y):
        self.Y = y
        self.R = Radius(y)

    def taylor(self, R):

        converged = False

        # intial range for the root:
        ta, tb = 0.0, inf
        ra, rb = 0.0, inf

        t = 0.0
        while not converged:
            r, rprime = self.R.taylor(t)

            if r <= R:
                ta, ra = t, r

            if r >= R:
                tb, rb = t, r

            # print "ta, t, tb =", ta, t, tb, "ra, r, rb =", ra, r, rb
            assert ta <= t <= tb
            assert ra <= r <= rb
            assert ra <= R <= rb

            if rprime != 0:
                dr = r - R
                dt = - dr / rprime
                # print "t=", t, "r=", r, "rprime=", rprime, "dt=", dt
                if ta < t + dt < tb:
                    # this accepts the Newton step:
                    t = t + dt
                elif rb - ra > 0.0:
                    # FIXME: specialized (Ridders) interpolation?
                    t = ta + dr * (tb - ta) / (rb - ra)
                else:
                    # already converged:
                    assert ra == r == rb
            else:
                # Jumped too far to the  right, t is so big that dy/dt
                # vanishes. FIXME: what if dy/dt is just orthogonal to
                # y(t) - y(0)?
                pass

            assert ta <= t <= tb

            if abs(r - R) <= 1.0e-13 * R or rprime == 0.0:
                converged = True

        y, yprime = self.Y.taylor(t)
        r, rprime = self.R.taylor(t)

        if rprime != 0.0:
            return y, yprime / rprime
        else:
            return y, zeros (shape (yprime))

def rk45(t1, x1, f, h, args=()):
    """Returns RK4 and RK5 steps as a tuple.

        >>> from numpy import exp

    For x(t) = x0 * exp(-t) the derivative is given by:

        >>> def f(t, x): return -x

        >>> x0 = 100.

        >>> rk45(0.0, x0, f, 1.0)
        (-63.46153846153845, -63.2852564102564)

    Actual solution changes by

        >>> x0 * exp(-1.0) - x0
        -63.212055882855765

    Euler step would have been:
        >>> 1.0 * (- x0)
        -100.0
    """

    k1 = h * f(t1, x1, *args)

    t2 = t1 + 1.0/4.0 * h
    x2 = x1 + 1.0/4.0 * k1
    k2 = h * f(t2, x2, *args)

    t3 = t1 + 3.0/8.0 * h
    x3 = x1 + 3.0/32.0 * k1 + 9.0/32.0 * k2
    k3 = h * f(t3, x3, *args)

    t4 = t1 + 12.0/13.0 * h
    x4 = x1 + 1932./2197. * k1 - 7200./2197. * k2 + 7296./2197. * k3
    k4 = h * f(t4, x4, *args)

    t5 = t1 + 1.0 * h
    x5 = x1 + 439./216. * k1 - 8. * k2 + 3680./513. * k3 - 845./4104. * k4
    k5 = h * f(t5, x5, *args)

    t6 = t1 + 0.5 * h
    x6 = x1 - 8./27.*k1 + 2.*k2 - 3544./2565. * k3 + 1859./4104.*k4 - 11./40. * k5
    k6 = h * f(t6, x6, *args)

    step4 = 25./216.*k1 + 1408./2565.*k3 + 2197./4104.*k4 - 1./5.*k5
    step5 = 16./135.*k1 + 6656./12825.*k3 + 28561./56430.*k4 - 9./50.*k5 + 2./55.*k6

    return step4, step5

def rk4(t1, x1, f, h, args=()):
    """Returns RK4 step.
    """

    k1 = h * f(t1, x1, *args)

    t2 = t1 + 1.0/4.0 * h
    x2 = x1 + 1.0/4.0 * k1
    k2 = h * f(t2, x2, *args)

    t3 = t1 + 3.0/8.0 * h
    x3 = x1 + 3.0/32.0 * k1 + 9.0/32.0 * k2
    k3 = h * f(t3, x3, *args)

    t4 = t1 + 12.0/13.0 * h
    x4 = x1 + 1932./2197. * k1 - 7200./2197. * k2 + 7296./2197. * k3
    k4 = h * f(t4, x4, *args)

    t5 = t1 + 1.0 * h
    x5 = x1 + 439./216. * k1 - 8. * k2 + 3680./513. * k3 - 845./4104. * k4
    k5 = h * f(t5, x5, *args)

    step4 = 25./216.*k1 + 1408./2565.*k3 + 2197./4104.*k4 - 1./5.*k5

    return step4

def rk5(t1, x1, f, h, args=()):
    """Returns RK5 step.
    """

    k1 = h * f(t1, x1, *args)

    t2 = t1 + 1.0/4.0 * h
    x2 = x1 + 1.0/4.0 * k1
    k2 = h * f(t2, x2, *args)

    t3 = t1 + 3.0/8.0 * h
    x3 = x1 + 3.0/32.0 * k1 + 9.0/32.0 * k2
    k3 = h * f(t3, x3, *args)

    t4 = t1 + 12.0/13.0 * h
    x4 = x1 + 1932./2197. * k1 - 7200./2197. * k2 + 7296./2197. * k3
    k4 = h * f(t4, x4, *args)

    t5 = t1 + 1.0 * h
    x5 = x1 + 439./216. * k1 - 8. * k2 + 3680./513. * k3 - 845./4104. * k4
    k5 = h * f(t5, x5, *args)

    t6 = t1 + 0.5 * h
    x6 = x1 - 8./27.*k1 + 2.*k2 - 3544./2565. * k3 + 1859./4104.*k4 - 11./40. * k5
    k6 = h * f(t6, x6, *args)

    step5 = 16./135.*k1 + 6656./12825.*k3 + 28561./56430.*k4 - 9./50.*k5 + 2./55.*k6

    return step5

# python ode.py [-v]:
if __name__ == "__main__":
    import doctest
    doctest.testmod()

# Default options for vim:sw=4:expandtab:smarttab:autoindent:syntax
