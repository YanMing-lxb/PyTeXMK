all:
	@python -m build

clean:
	@rm -fr build/ dist/ src/*.egg-info/
	@find . | grep __pycache__ | xargs rm -fr
	@find . | grep .pyc | xargs rm -f

html:
	@pandoc README.md > README.html

rst:
	@pandoc -s -t rst README.md > README.rst

test:
	@python tests/test.py

testwhl: clean all
	yes | pip uninstall pytexmk
	@pip install dist/*.whl
	@python tests/test.py -w
	yes | pip uninstall pytexmk
	@$(MAKE) clean

upload: clean all
	@twine upload dist/*
	@$(MAKE) clean