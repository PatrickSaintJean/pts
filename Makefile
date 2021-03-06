#
# Type "make -k" to run all tests.  Without -k make will stop at first
# failure it encounters.
#
# Type "make manual" to create a pdf version of the newest sources for
# the manual in doc subfolder
#
COSOPT = ./cosopt
TOOL = ./tools

src =	\
	common.py \
	searcher.py \
	ridders.py \
	npz.py \
	func.py \
	pes/mueller_brown.py \
	pes/rosenbrock.py \
	pes/leps.py \
	pes/gupta.py \
	pes/ab2.py \
	test/testfuns.py \
	ode.py \
	path.py \
	quat.py \
	bezier.py \
	chebyshev.py \
	zmat.py \
	bfgs.py \
	chain.py \
	steepest_descent.py \
	simple_descent.py \
	rc.py \
	vib.py \
	metric.py \
	threepointmin.py \
	cfunc.py \
	dimer_rotate.py \
	cosopt/multiopt.py \
	cosopt/conj_grad.py \
	qfunc.py \
	dct.py \
	paramap.py \
	dimer.py \
	sched.py \
	memoize.py \
	fopt.py \
	tools/path2plot.py \
	tools/path2tab.py \
	tools/path2xyz.py \

# dont call it "test" as we have a directory called so:
test-all: $(src:.py=.pyflakes) $(src:.py=.doctest) phony-targets

phony-targets: srcui srccosopt srctools

manual:
	$(MAKE) -C ./doc

# run a doctest on the module, return failure if any of the tests fail:
%.doctest: %.py
	(cd $(*D); python -c "import $(*F), doctest, sys; errs, _ = doctest.testmod($(*F)); sys.exit(bool(errs))")

%.pyflakes: %.py
	pyflakes $(<)

srcui:
	$(MAKE) -C ui

srccosopt:
	$(MAKE) -C $(COSOPT)

srctools:
	$(MAKE) -C $(TOOL)

