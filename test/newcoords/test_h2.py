#!/usr/bin/env python
"""
This script contains a simple example showing how the pathsearcher function
should be used and how the predefined functions from cfunc could be used to
generate the wanted function much easier.

The test system itself does not seems to provide a transition state at all.

For seeing how the pathsearcher runs just look at the code with choice 0.
For see how the functions in cfunc could be used together with some other
functions see the other choices.
"""
from pts.inputs.pathsearcher import pathsearcher
from ase.atoms import Atoms
from ase.calculators.lj import LennardJones
from pts.zmat import ZMat
from pts.test.testfuns import diagsandhight
from numpy import sqrt, asarray
from pts.cfunc import justcarts, with_globals, set, masked, with_equals
from pts.cfunc import pass_through

# choice = 0 should be the easiest case, best for understanding only
# the way pathsearcher should be used
choice = 0

# Pathsearcher needs an ASE atoms object or something which provides
# at least the functionality of mb_atoms example in mueller_brown.py
# Here a real atom object is generated with 2 H atoms:
h2 = Atoms("H2")

# before giving it to pathsearcher attach a valid calculator
h2.set_calculator(LennardJones())

d = 1.0

# Here the different ways of using the different functions are given
if choice == 0:
     """
     justcarts is used for only rearranging the input variables.
     From our functions we expect ouput of the three Cartesian coordinates
     for each atom in an array of the kind (N, 3)

     For further use in our pathsearcher we need the function itself
     and the two minima

     justcarts expects its input vector to be a one-dimensional array, as
     does pathsearcher.
     """
     func = justcarts()

     min1 = asarray([0., 0., 0.,0., 0., d])
     min2 = asarray([0., 0., 0.,0., 0., d*100.])

elif choice == 1:
    """
    It is intended for real internal coordinates: but works with every function:
    with_globals adds paramter for global rotation and translation.
    Notice that here the start geometries have 6 parameter more each.
    The first three of them describe an quaternion (or the vector v of unit quaternion
    e^iv. The rotation by this is obtained to every atom alone.
    The other three describe the global translation.
    """
    func = with_globals(justcarts())

    min1 = asarray([0., 0., 0.,0., 0., d, 0., 0., 0., 0.,0., 0.])
    min2 = asarray([0., 0., 0.,0., 0., d*100., 0., 0., 0., 0.,0., 0.])

elif choice == 2:
     """
     There is the possibility of having several functions merged to one, when
     each of them works on only a subset of the given parameter. This is done by
     function set.

     In this example each of the two atoms gets its own justcarts functions.
     Note that the functions mustn't overlap.
     """
     funcs = [justcarts(), justcarts()]
     dims = [3, 3]
     func = set(funcs, dims)

     min1 = asarray([0., 0., 0.,0., 0., d])
     min2 = asarray([0., 0., 0.,0., 0., d*100.])

elif choice == 3:
     """
     Function masked can be used to fix some parameters.
     One has to provide a logical mask, with False for fixed
     coordinates and True for the ones which should be optimized.
     The function to generate the Cartesian coordinates (in our
     example justcarts) will still get all the coordinates than before,
     but the interface to the outside wold will only contain the unfixed
     paramters. Function masked will deal with the extended requirements
     of the function func_raw.

     In this example only the z-coordinate of the last atom is
     kept optimizable.

     Note that now the internal coordinates only contain the
     unfixed coordinates. But the function needs to get an
     array of a complete set of coordinates (with the fixed ones)
     for initalizing (vector all in our example)
     """
     mask = [False] * 5 + [True]
     all = asarray([0., 0., 0.,0., 0., 0.])
     func = masked(justcarts(), mask, all)

     min1 = asarray([d])
     min2 = asarray([d*100.])

elif choice == 4:
     """
     If for example for symmetry reasons some coordinates are always the same (or always the
     negative of each other) this can be told to the function with_equals, which then
     can enlarge the array of internal coordinates before handing it over to the inner function
     which does not know that some of its parameter are just the same.
     There is furthe the possibility of keeping some other paramters fixed.

     The mask contains integer number telling which number of the smaller internal coordinate
     array should be used for given place of array for the inner function. A negative of a number
     means that the negative of the value from the given number is used. Note that other than in
     python array numbering the first element of the array is described by 1. 0 stands for a fixed
     coordinate.

     In this example the inner function is just our example function justcarts expecting 6 coordinates
     (three per atom). The mask says that the first element of the array should be used for the first
     and (its negative) for the third coordinate, while the second element is used for 4 and 5 of extended
     coordinates. The last element is used for the last of the extended coordinates, while the second of the
     extended coordinates is given by the default. Be aware that if there wasn't a fixed coordinate the start
     value needs not to contain any valid data.
     The arrays for the path contain here only three elements.
     """
     mask = [1, 0, -1, 2, 2, 3]
     start = asarray([0., 0., 0., 0., 0., 0.])
     func = with_equals(justcarts(), mask, start)

     min1 = asarray([0., 1.,d])
     min2 = asarray([0., 1., d*100.])

elif choice == 5:
     """
     Functions of cfunc can be stacked: here first a set of two justcarts functions, one
     for each atom is build, then with equals the positions of atom one and the two zero
     positions of atom two are set equal. The function used for pathsearcher than puts
     an additional mask over the two first variables, keeping them fixed with 0.

     The internal geometries thus do only contain a single entry.
     """
     funcs = [justcarts(), justcarts()]
     dims = [3, 3]
     func2 = set(funcs, dims)

     mask1 = [1, 1, 1, 2, 2, 3]
     start = asarray([0., 0., 0., 0., 0., 0.])
     func1 = with_equals(func2, mask1, start)

     mask = [False] * 2 + [True]
     all = asarray([0., 0., 0.])
     func = masked(func1, mask, all)

     min1 = asarray([d])
     min2 = asarray([d*100.])

elif choice == 6:
     """
     Stacked cfunc's 2: first two justcarts functions are defined for each atom,
     then with_equals is used for fixing the first five coordinates.
     """
     funcs = [justcarts(), justcarts()]
     dims = [3, 3]
     func2 = set(funcs, dims)

     mask1 = [0, 0, 0, 0, 0, 1]
     start = asarray([0., 0., 0., 0., 0., 0.])
     func = with_equals(func2, mask1, start)

     min1 = asarray([d])
     min2 = asarray([d*100.])

elif choice == 7:
     """
     Inner functions for the cfunc set do not need to be so distributed that
     each of them covers only complete atoms. Function justcarts would get
     problems with that though, thus here pass_through as the simplest possible
     function is used. The first function goes over the x and y coordinate of the
     first atom, the second functiontakes all the rest. The functions with_equals
     further reduce the number of variables.
     """
     mask1 = [1, 1]
     start1 = asarray([0., 0.])
     func1 = with_equals(pass_through() ,mask1, start1)

     mask2 = [1, 1, 1, 2]
     start2 = asarray([0., 0., 0., 0.])
     func2 = with_equals(pass_through(), mask2, start2)

     funcs = [func1, func2]
     dims = [1, 2]
     func = set(funcs, dims)

     min1 = asarray([0., 0., d])
     min2 = asarray([0., 0., d*100.])

# pathsearcher wants its inital path geometries on a string
# there need to be at least to of them (of the two minima)
init_path = [min1, min2]

# This is the function call of pathsearcher, here besides the function needed in any case
# some of the default parameter are overwritten, so the convergence criteria and the maximal iteration number
# are reset and the new searchingstring method is used to calculate the path
pathsearcher(h2, init_path, funcart = func, ftol = 0.1, maxit = 4, beads_count = 5, cos_type = "searchingstring")

