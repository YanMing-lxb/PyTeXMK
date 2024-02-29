all:
	python -m build

clean:
	rm -fr build/ dist/ src/*.egg-info/
	find . | grep __pycache__ | xargs rm -fr
	find . | grep .pyc | xargs rm -f

html:
	pandoc README.md > README.html

rst:
	pandoc -s -t rst README.md > README.rst

test:
	python3 tests/test.py

upload:
	twine upload dist/*