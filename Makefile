
PACKAGE_NAME=tff
DEPENDENCIES=
PYTHON=python
RM=rm -rf

.PHONY: smoketest nosetest build setuptools install uninstall clean update

build: update_license_block smoketest
	$(PYTHON) setup.py sdist
	python2.5 setup.py bdist_egg
	python2.6 setup.py bdist_egg
	python2.7 setup.py bdist_egg

update_license_block:
	chmod +x update_license
	find . -type f | grep '\(.py\|.c\)$$' | xargs ./update_license

setuptools:
	$(PYTHON) -c "import setuptools" || \
		curl http://peak.telecommunity.com/dist/ez_setup.py | $(PYTHON)

cbuild:
	cc -fno-strict-aliasing -fno-common -dynamic -arch x86_64 -arch i386 -g -O0 -pipe -fno-common -fno-strict-aliasing -fwrapv -mno-fused-madd -DENABLE_DTRACE -DMACOSX -Wall -Wstrict-prototypes -Wshorten-64-to-32 -g -fwrapv -O0 -Wall -Wstrict-prototypes -DENABLE_DTRACE -arch x86_64 -arch i386 -pipe -I/System/Library/Frameworks/Python.framework/Versions/2.7/include/python2.7 -c ctff.c -o tff/ctff.o
	cc -bundle -undefined dynamic_lookup -arch x86_64 -g -arch i386 -Wl,-F. tff/ctff.o -o tff/ctff.so

install: smoketest setuptools
	$(PYTHON) setup.py install

uninstall:
	for package in $(PACKAGE_NAME) $(DEPENDENCIES); \
	do \
		pip uninstall -y $$package; \
	done

clean:
	for name in dist build *.egg-info htmlcov *.pyc *.o; \
		do find . -type d -name $$name || true; \
	done | xargs $(RM)

smoketest:
	$(PYTHON) setup.py test

nosetest:
	if $$(which nosetests); \
	then \
	    nosetests --with-doctest \
	              --with-coverage \
	              --cover-html \
	              --cover-package=sskk; \
	else \
	    $(PYTHON) setup.py test; \
	fi

update: clean smoketest
	$(PYTHON) setup.py register
	$(PYTHON) setup.py sdist upload
	python2.5 setup.py bdist_egg upload
	python2.6 setup.py bdist_egg upload
	python2.7 setup.py bdist_egg upload

