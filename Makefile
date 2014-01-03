
PACKAGE_NAME=tff
PYTHON=python

all: smoketest
	$(PYTHON) setup.py bdist

update_license_block:
	chmod +x update_license
	find . -type f | grep '\(.py\|.c\)$$' | xargs ./update_license

cbuild:
	cc -fno-strict-aliasing -fno-common -dynamic -arch x86_64 -arch i386 -g -O0 -pipe -fno-common -fno-strict-aliasing -fwrapv -mno-fused-madd -DENABLE_DTRACE -DMACOSX -Wall -Wstrict-prototypes -Wshorten-64-to-32 -g -fwrapv -O0 -Wall -Wstrict-prototypes -DENABLE_DTRACE -arch x86_64 -arch i386 -pipe -I/System/Library/Frameworks/Python.framework/Versions/2.7/include/python2.7 -c ctff.c -o tff/ctff.o
	cc -bundle -undefined dynamic_lookup -arch x86_64 -g -arch i386 -Wl,-F. tff/ctff.o -o tff/ctff.so

build: smoketest
	$(PYTHON) setup.py sdist
	python2.6 setup.py bdist_egg
	python2.7 setup.py bdist_egg

install:
	$(PYTHON) -c "import setuptools" || curl http://peak.telecommunity.com/dist/ez_setup.py | python
	$(PYTHON) setup.py install

uninstall:
	yes | pip uninstall $(PACKAGE_NAME) 
	
clean:
	rm -rf dist/ build/ *.egg-info *.pyc **/*.pyc

smoketest:
	$(PYTHON) setup.py test
	./test.py

update: clean test
	$(PYTHON) setup.py register
	$(PYTHON) setup.py sdist upload
	python2.6 setup.py bdist_egg upload
	python2.7 setup.py bdist_egg upload

