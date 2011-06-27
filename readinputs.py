#!/usr/bin/env python
"""
This tool is the interface to the string and NEB methods.

Usage:

  pathsearcher.py --calculator CALC GEOM1 GEOM2

For either string or NEB methods one needs to specify at least two geometries
and the calculator.

GEOMETRY

Geometries can be provided as files, which can be interpreted by ASE. This
includes xyz-, POSCAR, and gx-files. File format is in part determied from the
file name or extension, e.g. POSCAR and gx-files by the presence of "POSCAR" or
"gx" substrings. If the format is not extractable from the filename it can be
given as an addtional parameter as --format <format> . The Values for <format>
are gx or are in the list of short names in the ASE documentation.

If the calculation should be done in internal (or mixed coordinate system) one gives
the geometries in cartesians  and specifies additionally the zmatrix/zmatrices
They will then be given by writing --zmatrix zmat_file. It is supposed that the first atom
of each zmatrix is the uppermost not yet used atom of ones given.

ZMATRIX

A zmatrix may look something like:

""
C
H 1 var1
H 1 var2 2 var3
H 1 var4 2 var5 3 var6
H 1 var7 2 var8 4 var9
""

The first element of each line is supposed to be the name of the atom.
Then follows the connectivity matrix, where for each appearing variable a
name is given. The connectivities are given by the line number of the atom,
starting with 1. First variable is always the length, second the angle and
third the dihedral angle. If variable names appear more than once these variables
are set to the same value. Giving a variable name as another variable name with a
- in front of it, the values are always set to the negative of the other variable.

SETTING VARIABLES

There are some other parameters specified, which decide on how the program will
run. There is a list of default parameters

  pathsearcher.py --defaults

shows all of them They can be changed in two different ways: by including in
the parameters in the calculation above:

  --paramfile filename

all the variables could be set in the file filename or by giving directly

  --parameter_to_change new_value

this only works for parameters which take a string, a float or a integer
(always a single number, or a name), ch tells if they could changed by giving
the parameter values directly in the parameter list, so for example

  --name NewName

would set the name to NewName in the parameters If the same variable is set in
both the paramfile and directly, the directly set value is taken

There exists:
Parameter    ch     short description
------------------------------------------------
 "method"  yes      what calculation is really wanted, like neb, string,
                    growingstring or searchingstring, if using paratools <method> this
                    is set automatically
 "opt_type"  yes    what kind of optimizer is used for changing the geometries
                    of the string, as default the new multiopt is used for the
                    string methods, while neb is reset to ase_lbgfs
 "pmax"      yes    maximal number of CPUs per bead, with our workarounds normaly
                    only indirect used
 "pmin"      yes    minimal number of CPUs per bead, with our workarounds normaly
                    only indirect used
 "cpu_architecture" no  descriebes the computer architecture, which should be used,
                    with our workaround only indirect used, pmax, pmin and
                    cpu_architecture should be adapted to each other
 "name"      yes    the name of the calculation, appears as basis of the names
                    for all the output, needn't be set, as a default it takes
                    the cos_type as name
 "calculator" no    the quantum chemstry program to use, like Vasp or ParaGauss
 "placement"  no    executable function for placing processes on beads, only
                    used for advanced calculations
 "cell"       no    the cell in which the molecule is situated
 "pbc"        no    which cell directions have periodic boundary conditions
 "mask"       no    which of the given geometry variables are supposed to be
                    changed (True) and which should stay fix during the
                    calculation (False), should be a string containing for each
                    of the variables the given value. The default does not set
                    this variable and then all of them
                    are optimized
 "beads_count" yes  how many beads (with the two minima) are there at maximum
                    (growingstring and searchingstring start with less)
 "ftol"       yes   the force convergence criteria, calculation stops if
                    RMS(force) < ftol
 "xtol"       yes   the step convergence criteria, only used if force has at
                    least ftol * 10
 "etol"       yes   energy convergence criteria, not really used
 "maxit"      yes   if the convergence criteria are still not met at maxit
                    iterations, the calculation is stopped anyhow
 "maxstep"    yes   the maximum step a path can take
 "spring"  yes   the spring constant, only needed for neb
 "pre_calc_function"  no function for precalculations, for gaussian ect.
 "output_level" yes the amount of output is decided here
                       0  minimal output, not recommended
                          only logfile, geometries of the beads for the last
                          iteration (named Bead?) and the output needed for
                          the calculation to run
                       1  recommended output level (default) additional the
                          ResultDict.pickle (usable for rerunning or extending the
                          calculation without having to repeat the quantum
                          chemical calculations) and a path.pickle of the last
                          path, may be used as input for some other tools,
                          stores the "whole" path at it is in a special foramt
                       2  additional a path.pickle for every path, good if
                          development of path is
                          wanted to be seen (with the additional tools)
                       3  some more output in every iteration, for debugging ect.

 "output_path"   yes   place where most of the output is stored, thus the
                       working directory is not filled up too much
 "output_geo_format" yes ASE format, to write the outputgeometries of the
                       last iteration to is xyz as default, but can be changed
                       for example to gx or vasp (POSCAR)

Additional informations can be taken from the minima ASE inputs. The ase atoms
objects may contain more informations than only the chemical symbols and the
geometries of the wanted object. For example if reading in POSCARs there are
additional informations as about the cell (pbc would be also set automatically
to true in all directions). This informations can also be read in by this tool,
if they are available, they are only used, if these variables still contain the
default parameters.  Additionally ase can hold some constraints, which may be
taken from a POSCAR or set directly. Some of them can be also used to generate
a mask. This is only done if cartesian coordinates are used.

CALCULATOR

The calculator can be given in ASE format. It can be set in the paramfile or in
an own file via

  --calculator calc_file

Additionally one can use some of the default specified calculators by for
example:

  --calculator default_vasp

The way to set up those calculators is given best on the ASE homepage at:

  https://wiki.fysik.dtu.dk/ase/ase/calculators/calculators.html#module-calculators

Reuse RESULTS FROM PREVIOUS CALCULATIONS

It is possible to store the results of the quantum chemical calculations (which
are the computational most expensive part of the calculation) in a
ResultDict.pickle file. It is done by default for an output level with at least
1. If a calculation with the same system should be done, or the system should
be repeated, this results can be reused (the QC- program mustn't be changed, as
well as the geometries of the two minima). To reuse this results say in the
parameters:

  --old_results filename

filename should be directed on the file (with location) where the Results are
stored

INITIAL PATH

One can provide the inital path by giving geometries as for the two minima
(all in the same format, please). In this case the call of the method would be
something like

  pathsearcher.py --parmeter some_params minima1 bead2 bead3 bead4  minima2

or for example:

  pathsearcher.py --parmeter some_params POSCAR? POSCAR??

The number of inital points and beads need not be the same.
Be aware that there are sometimes differnet interpolations between two beads possible.
So for example the dihedral angle (or the quaternion angle) have a 2*pi periodicity.
The interpolation points between two same (Cartesian) geometries but with different of these
angles should normally differ. Here the angles are choosen such that they differ of
at least pi (the shortest possible way in these coordinates). If another path is wanted
one needs to specify more points of the inital path to force the pathsearcher to
take the wanted path (if two paths differ completly at the beginning they would hardly
never converge to the same path at the end, thus it makes sense to make sure that
the inital path is fitting)

EXAMPLES

A minimal one:

  pathsearcher.py --calculator default_lj left.xyz right.xyz

Having several POSCAR's for the inital path (from POSCAR0 to POSCAR11). A
parameterfile (called params.py) should hold some parameters, so especially the
calculator) but ftol is anyway 0.07

  pathsearcher.py --paramfile params.py --ftol 0.07 --name Hydration POSCAR? POSCAR??
"""
from pts.pathsearcher_defaults.params_default import default_params, are_floats, are_ints
from pts.common import file2str
from pts.readcos import read_geos_from_file, read_zmt_from_file
from pts.cfunc import Justcarts, With_globals, Mergefuncs, Masked, With_equals
from pts.zmat import ZMat
from pts.quat import Quat, uquat, quat2vec
from numpy import array, pi
from numpy.linalg import norm
from ase.calculators import *
from pts.qfunc import constraints2mask

def interprete_input(args):
    """
    Gets the input of a pathseracher calculation and
    interpretes it
    """
    # first read in geometries and sort parameter
    geos, geo_dict, zmat, add_param, paramfile, old_results = interpret_sysargs(args)
    # most parameters are stored in a dictionary, default parameters are stored in
    # pathsearcher_defaults/params_default
    para_dict = create_params_dict(add_param, paramfile)
    geo_dict["mask"] = para_dict["mask"]
    # geometries are given in Cartesian, here transform them to internals
    # calculator for forces, internal start path, function to transform internals to Cartesian coordinates,
    # the numbers where dihedrals are, which of the function parts have global positions, how many
    # variables belong to the function part
    atoms, init_path, funcart, dih, quats, lengt = get_geos(geos, geo_dict, zmat)
    # dihedrals and quaternions have 2pi periodicity, adapt them if needed
    init_path = ensure_short_way(init_path, dih, quats, lengt)
    # if a mask has been provided, some variables are not optimized
    funcart, init_path = get_masked(funcart, atoms, geo_dict, zmat == None, init_path)
    # this is everything that is needed for a pathsearcher calculation
    return atoms, init_path, funcart, para_dict

def restructure(dat):
    """
    dat is a list of dataobjects, containing num different results
    those results will be extracted and returned as num list for each of the results
    Some sum will also be given. 
    Only usable for the output of a read_zmt_from_file/ read_zmt_from_string call
    Used to mix several of this calls to one output

    a: names
    b: z-matrix connectivities
    c: number_of vars
    d: multiplicity
    e: dihedral_nums
    f: how many Cartesian coordinates are covered
    g: how many variables (internals)
    h: how many variables (Cartesians)
    """
    a = []
    b = []
    c = []
    d = []
    e = []
    f = 0
    g = []
    h = []
    for da in dat:
        a1, b1, c1, d1, e1, f1 = da
        a = a + a1
        b.append(b1)
        c.append(c1)
        d.append(d1)
        e.append(e1)
        f2, f3 = f1
        f = f + f2
        g.append(f3)
        h.append(f2)

    return a, b, c, d, e, f, g, h

def get_geos(geos, dc, zmi):
    """
    Creates the inital path, the atoms object and the
    function for changing between internal and Cartesian
    (Cartesian to be fed into atoms object)
    """
    # read cartesian data
    at, geo_carts = read_geos_from_file(geos, dc["format"])

    if "calculator" in dc.keys():
          calculator = None
          str1 = file2str(dc["calculator"])
          exec(str1)
          at.set_calculator(calculator)


    # RETURN POINT: only Cartesian geometry
    if zmi == []:
       geo_int = array([ge.flatten() for ge in geo_carts])
       return at, geo_int, Justcarts(), [[]], [False], [len(geo_carts[0].flatten())]

    len_carts = len(geo_carts[0].flatten())

    # extract data from (several) zmatrices
    datas = [read_zmt_from_file(zm) for zm in zmi]
    names, zmat, var_nums, mult, d_nums, size_sys, size_nums, size_carts = restructure(datas)

    # decide if global positioning is needed
    with_globs = (len_carts > size_sys) or len(zmat) > 1
    # first only the zmatrix functions, allow multiple use of variables
    funcs = []
    quats = []

    # build function for every zmatrix
    for i, zm, va_nm, mul in zip(range(len(var_nums)), zmat, var_nums, mult):
          fun = ZMat(zm)

          # some variables are used several times
          if mul > 0:
             fun = With_equals(fun, va_nm)

          # global positioning needed
          if with_globs:
             fun = With_globals(fun)
             quats.append(True)
             # attention, this changes number of internal coordinates
             # belonging to this specific zmatrix
             size_nums[i] = size_nums[i] + 6
          else:
             quats.append(False)

          funcs.append(fun)

    # if not all variables are used up, the rest are in Cartesians
    if len_carts > size_sys:
         funcs.append(Justcarts())
         # there is also some need to specify their sizes
         size_nums.append(len_carts - size_sys)
         size_carts.append(len_carts - size_sys)
         quats.append(False)
         d_nums.append([])

    # how many atoms per single function
    # needed for Mergefuncs.pinv
    size_carts = [s/3. for s in size_carts]

    # now merge the functions to one:
    if len(size_nums) > 1:
        func = Mergefuncs(funcs, size_nums, size_carts)
    else:
        # no need to merge a single function
        func = funcs[0]

    # transform Cartesians to internals (all functions used
    # till know have pseudoinverse)
    geo_int = [func.pinv(geo) for geo in geo_carts]
    return at, geo_int, func, d_nums, quats, size_nums

def reduce(vec, mask):
    """
    Function for generating starting values.
    Use a mask to reduce the complete vector.
    """
    vec_red = []
    for i, m in enumerate(mask):
         if m:
             vec_red.append(vec[i])
    return array(vec_red)


def get_masked(int2cart, at, geo_carts, zmat, geos):
    """
    There are different ways to provide a mask (fixes some
    of the variables), check for them and use a masked
    func if required
    """

    mask = None
    if "mask" in geo_carts.keys():
       mask = geo_carts["mask"]
    elif zmat:
       mask = constraints2mask(at)

    if not mask == None:
       int2cart = Masked(int2cart, mask, geos[0])
       geos = [reduce(geo, mask) for geo in geos]

    return int2cart, geos

def ensure_short_way(init_path, dih, quats, lengt):
    """
    Ensures that between two images of init_path the shortest way is taken
    Thus that the dihedrals differ of less than pi and that the
    quaternions are also nearest as possible
    """
    for i_n1, m2 in enumerate(init_path[1:]):
       m1 = init_path[i_n1]
       # m1, m2 are two succeding images

       start = 0
       # first the dihedrals:
       # differences between two succiding beads should be smaller than
       # pi
       for  l, di in zip(lengt, dih):
            for d in di:
               delta = m2[d+start] - m1[d+start]
               while delta >  pi: delta -= 2.0 * pi
               while delta < -pi: delta += 2.0 * pi
               m2[d+start] = m1[d+start] + delta
            start = start + l

       start = 0

       # now Quaternions:
       # q2 can be decribed as q2 = q1 * diff
       # make quaternion diff minimal (could have
       # angle smaller than pi)
       for l, q in zip(lengt, quats):
           # Systems without global positioning should not be
           # changed here, for the others one knows already where
           # to find the quaternions
           if q:
               a = l - 6 + start
               b = l - 3 + start
               # the two quaternions to compare
               q1 = Quat(uquat(m1[a:b]))
               q2 = Quat(uquat(m2[a:b]))

               # q2 = q1 * q_diff (then transform to vector)
               # FIXME: is there an easy way to do this in
               #        Quat objects only
               diff = quat2vec(q2 / q1)

               delta = norm(diff)

               if not delta == 0:
                   diff = diff / delta

               # normalize the interval between two angles:
               while delta >  pi: delta -=  2.0 * pi
               while delta < -pi: delta +=  2.0 * pi

               diff = diff * delta

               # q2 = q1 * q_diff
               m2[a:b] = quat2vec(q1 * Quat(uquat(diff)))

           start = start + l

    return init_path


def interpret_sysargs(rest):
    """
    Gets the arguments out of the sys arguments if pathsearcher
    is called interactively

    transforms them to parameter and input for pathsearcher
    """

    if "--help" in rest:
        print __doc__
        exit()

    if "--defaults" in rest:
        print "The default parameters for the path searching algorithm are:"
        for param, value in default_params.iteritems():
            print "    %s = %s" % (str(param), str(value))
        exit()

    paramfile = None
    old_results = None
    geo_dict = { "format": None}
    geos = []
    add_param = {}
    zmatrix = []

    # Now loop over the arguments
    for i in range(len(rest)):
        if rest == []:
            # As one reads in usually two at once, one might run out of
            # arguements before the loop is over
            break
        elif rest[0].startswith("--"):
            # this are the options given as
            # --option argument
            o = rest[0][2:]
            a = rest[1]
            # filter out the special ones
            if o == "paramfile":
                # file containing parameters
                paramfile = file2str(a)
            elif o in ("old_results"):
                # file to take results from previous calculations from
                old_results = a
            elif o in ("zmatrix"):
                # zmatrix if given separate to the geometries
                zmatrix.append(a)
            elif o in ("format", "calculator"):
                # only needed to build up the geometry
                geo_dict[o] = a
            elif o in ("mask"):
                # needed to build up the geometry and wanted for params output
                add_param[o] = eval("%s" % (a))
            else:
                assert(o in default_params.keys())
                # suppose that the rest are setting parameters
                # compare the default_params
                if o in are_floats:
                    add_param[o] = float(a)
                elif o in are_ints:
                    add_param[o] = int(a)
                else:
                    add_param[o] = a

            rest = rest[2:]
        else:
            # all other things are supposed to be geometries
            geos.append(rest[0])
            rest = rest[1:]

    return geos, geo_dict, zmatrix, add_param, paramfile, old_results

def create_params_dict(new_params, paramfile):
    """
    create the parameter dictionary for the pathsearcher routine
    """
    # set up parameters (fill them in a dictionary)
    params_dict = default_params.copy()

    # noverwrite by those given in parameter file
    if not paramfile == None:
        params_dict = reset_params_file(params_dict, paramfile)

    # ovewrite all of them by those given directly into the input
    for key in new_params.keys():
        if key in params_dict:
            params_dict[key] = new_params[key]
        else:
            print "ERROR: unrecognised variable in parameter"
            print "The variable",key, "has not been found"
            print "Please check if it is written correctly"
            exit()

    # Special treatment, set name in any case and check for not allowed combinations
    if params_dict["name"] == None:
        params_dict["name"] = str(params_dict["method"])

    if params_dict["method"].lower() == "neb":
        if params_dict["opt_type"] == "multiopt":
            print "The optimizer %s is not designed for working with the method neb", params_dict["opt_type"]
            params_dict["opt_type"] = "ase_lbfgs"
            print "Thus it is replaced by the the optimizer", params_dict["opt_type"]
            print "This optimizer is supposed to be the default for neb calculations"

    return params_dict

def reset_params_file(params_dict, lines):
    """
    overwrite params in the params dictionary with the params
    specified in the string lines (can be the string read from a params file

    checks if there are no additional params set
    """
    # the get the params out of the file is done by exec, this
    # will also execute the calculator for example, we need ase here
    # so that the calculators from there can be used
    import ase
    from ase.calculators import *

    # execute the string, the variables should be set in the locals
    glob_olds = locals().copy()
    print glob_olds.keys()
    exec(lines)
    glob = locals()
    print glob.keys()

    for param in glob.keys():
        if not param in glob_olds.keys():
             if param == "glob_olds":
                 # There is one more new variable, which is not wanted to be taken into account
                 pass
             elif not param in params_dict.keys():
                 # this parameter are set during exec of the parameterfile, but they are not known
                 print "WARNING: unrecognised variable in parameter input file"
                 print "The variable", param," is unknown"
             else:
                 # Parameters may be overwritten by the fileinput
                 params_dict[param] = glob[param]

    return params_dict
