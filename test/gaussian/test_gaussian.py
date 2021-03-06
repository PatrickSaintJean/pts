import sys
import unittest
import os
import time

import numpy
import ase

import pts 
import pts.coord_sys as cs
import pts.gaussian as g
import pts.common as common
from pts.common import file2str

print "__file__", __file__


class TestGaussianDriver(pts.test.MyTestCase):

    def setUp(self):
        self.original_dir = os.getcwd()
        new_dir = os.path.dirname(__file__)
        if new_dir != '':
            os.chdir(new_dir)

    
    def tearDown(self):
        os.chdir(self.original_dir)

    def test_gaussian_benzyl(self):
      
        g = pts.gaussian.Gaussian(charge=0, mult=2)
        b = cs.XYZ(file2str("benzyl.xyz"))
        b.set_calculator(g)
        print b.get_forces()

    def test_gaussian_water(self):
      
        g = pts.gaussian.Gaussian(charge=0, mult=2)
        b = cs.ZMatrix(file2str("H2O.zmt"))
        b.set_calculator(g)
        self.assertRaises(pts.gaussian.GaussDriverError, b.get_forces)

        g = pts.gaussian.Gaussian(charge=-1, mult=2)
        b = cs.ZMatrix(file2str("H2O.zmt"))

        expect = numpy.array([ 0.0632226, -0.00272265,  0.])
        b.set_calculator(g)
        actual = b.get_forces()

        self.assertAlmostEqualVec(expect, actual)

    def test_gaussian_chkpointing(self):
      
        print """Testing that for a tricky wavefunction, the gaussian driver
will read in a guess and achieve speedier convergence the second time around."""
        print "This test will take around 20 seconds..."
        start = time.time()
        g = pts.gaussian.Gaussian(mult=2)
        b = cs.XYZ(file2str("benzyl.xyz"))
        b.set_calculator(g)
        b.get_potential_energy()
        t0 = time.time() - start
        coords = b.get_internals()
        coords *= 1.05
 
        start = time.time()
        b.set_internals(coords)
        b.get_potential_energy()
        t1 = time.time() - start

        print "Times for first calc and second calculations:", t0, t1
        print "Ratio of times", (t1/t0)
        low, high = 0.3, 0.6
        print "Must be between %f and %f" % (low, high)

        self.assert_(low < t1/t0 < high)



def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestGaussianDriver)

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([TestGaussianDriver("test_gaussian_chkpointing")]))


