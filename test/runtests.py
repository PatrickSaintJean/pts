#!/usr/bin/env python

import unittest
import sys
print "tsdf"
import aof.test.numerical as numerical
import aof.test.zmatrix as zmatrix
import aof.test.searcher as searcher
import aof.test.coord_sys as coord_sys
import aof.test.gaussian as gaussian

print "here"
test_suites = {
    'numerical':    numerical.suite(),
#    'zmatrix':  zmatrix.suite(), # superseded by coord_sys
    'neb':          searcher.suite_neb(),
    'coord_sys':    coord_sys.suite(),
    'gaussian':     gaussian.suite()
    }


alltests = unittest.TestSuite(test_suites.values())
test_suites['all'] = alltests

tests = sys.argv[1:]

if len(tests) == 0:
    tests.append("all")

if __name__ == "__main__":
    for test in tests:
        if not test in test_suites:
            print "Test", test, "not found"
        else:
            print "Running test suite:", test
            unittest.TextTestRunner(verbosity=4).run(test_suites[test])
