
all:
	
run:
	python test/test.py

install:
	curl http://peak.telecommunity.com/dist/ez_setup.py | python
	python setup.py install

clean:
	rm -rf dist/ build/ tff.egg-info

update:
	python setup.py register
	python setup.py sdist upload
	python2.6 setup.py bdist_egg upload
	python2.7 setup.py bdist_egg upload

