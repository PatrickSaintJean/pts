#!/usr/bin/env python

import sys

import aof
import ase

"""BEGIN USER DEFINED SETTINGS"""

reagent_files = ["Bz_H2O-1.xyz", "Bz_H2O-2.xyz"]
name = "_to_".join(reagent_files)

# mask of variables to freeze
# True => optimised
mask = [False for i in range(12*3)] + [True for i in range(3*3)]

# calculator 3-tuple: 
# (constructor, arguments (list), keyword arguments (dictionary))
calc_tuple = (aof.qcdrivers.Gaussian, [], {'basis': '3-21G'})

# scheduling information
# Field 1: list of processors per node e.g.
#  - [4] for a quad core machine
#  - [1] for a single core machine
#  - [1,1,1] for a cluster (or part thereof) with three single processor nodes
#  - [4,4,4,4] for a cluster with 4 nodes, each with 4 cores
# Field 2: max number of processors to run a single job on
# Field 3: normal number of processors to run a single job on
available, job_max, job_min = [4], 2, 1

params = {
    # name of calculation, output files are named based on this
    'name': name,

    # calculator specification, see above
    'calculator': calc_tuple,

    # name of function to generate placement commant
    'placement': aof.common.place_str_dplace, 

    # cell shape, see ASE documentation
    'cell': None, 

    # cell periodicy, can be None
    'pbc': [False, False, False],

    # variables to mask, see above
    'mask': mask} 

beads_count = 4  # number of beads
tol = 0.01       # optimiser force tolerance
maxit = 1        # max iterations
spr_const = 5.0  # NEB spring constant (ignored for string)
growing = False  # is the string growing

"""END USER DEFINED SETTINGS"""

mol_strings = aof.read_files(reagent_files)
mi          = aof.MolInterface(mol_strings, params)
procs_tuple = (available, job_max, job_min)
calc_man    = aof.CalcManager(mi, procs_tuple)

CoS = aof.searcher.GrowingString(mi.reagent_coords, 
          calc_man, 
          beads_count,
          rho = lambda x: 1,
          growing=growing,
          parallel=True,
          head_size=None)

# dump the final shape of the string
aof.dump_steps(CoS)

# callback function
mycb = lambda x: aof.generic_callback(x, mi, CoS, params)

import cosopt.lbfgsb as so

while True:
    opt, energy, dict = so.fmin_l_bfgs_b(CoS.obj_func,
                                  CoS.get_state_as_array(),
                                  fprime=CoS.obj_func_grad,
                                  callback=mycb,
                                  pgtol=tol,
                                  maxfun=maxit)
    if not growing or not CoS.grow_string():
        break
    
print opt
print dict

# get best estimate(s) of TS from band/string
tss = CoS.ts_estims()

for ts in tss:
    e, v = ts
    cs = mi.build_coord_sys(v)
    print cs.xyz_str()

