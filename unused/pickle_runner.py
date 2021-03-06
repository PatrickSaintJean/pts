#!/usr/bin/env python

import sys
import getopt
import os
import pts.common as common
import pts.coord_sys as coord_sys
import pickle
#from pts.sched import Item
#from common import Job.G

import ase

def usage():
    print "Usage: " + sys.argv[0] + " [options] calculator.pickle molecule.pickle"
    print "       -o: optimise"

class PickleRunnerException(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ho", ["help", "optimise"])
        except getopt.error, msg:
             raise PickleRunnerException(msg)
        
        mode = "calc_eg"
        for o, a in opts:
            if o in ("-h", "--help"):
                usage()
                return 0
            if o in ("-o", "--optimise"):
                mode = "optimise"
            else:
                usage()
                return -1

        if len(args) != 1:
            raise PickleRunnerException("Exactly one input file must be given.")

#        calc_filename = os.path.abspath(args[0])
        mol_filename = os.path.abspath(args[0])

#        calc_pickled = open(calc_filename, "rb")
        mol_pickled = open(mol_filename, "rb")

        print "About to unpickle"
        # create atoms object based on pickled inputs
        mol, data = pickle.load(mol_pickled)
        f = None

        print "mol", str(mol)


        #if not mol._atoms.get_calculator():
        #    raise PickleRunnerException("Molecule object had no calculator.")

        jobname =  mol_filename.split(".")[0]

        # setup directories, filenames
        isolation_dir =  jobname
        print "isolation_dir", isolation_dir

        old_dir = os.getcwd()

        # if a tmp directory is specified, then use it
        tmp_dir = common.get_tmp_dir()
        os.chdir(tmp_dir)

        # Create/change into isolation directory. This directory holds temporary files
        # specific to a computation, not including input and output files.
        if not os.path.exists(isolation_dir):
            os.mkdir(isolation_dir)
        os.chdir(isolation_dir)


        # Perform final tasks, e.g. copy the 
        # WAVECAR or blah.chk file here.
        if f != None:
            if not callable(f):
                raise PickleRunnerException("Supplied function was neither callable nor None.")
            f(mol.get_calculator(), data)

        result_file = os.path.join(tmp_dir, jobname + common.OUTPICKLE_EXT)

        if mode == "calc_eg":
            # run job using ASE calculator
            print "Running pickle job in", os.getcwd()

            print "isolation_dir", isolation_dir
            print "type(mol._atoms.calc)", type(mol._atoms.calc)
            g = - mol.get_forces().flatten()
            assert len(g.shape) == 1
            e = mol.get_potential_energy()

            result = (e, g, os.getcwd())

            os.chdir(old_dir)

            pickle.dump(result, open(result_file, "w"), protocol=2)

            # just for testing...
            print pickle.load(open(result_file, "r"))

        elif mode == "optimise":
            optim = ase.LBFGS(mol, trajectory='opt.traj')
            optim.run(steps=10)
            os.chdir(old_dir)

            ase.io.write(result_file, mol._atoms, format="traj")
        else:
            raise PickleRunnerException("Unrecognised mode: " + mode)

    except PickleRunnerException, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    except IOError, err:
        print >>sys.stderr, err
        return -1

if __name__ == "__main__":
    sys.exit(main())


