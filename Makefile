all:
	@python -m build


clean:
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	@if exist build rmdir build /s /q
	@if exist dist rmdir dist /s /q
	@if exist src\pytexmk.egg-info rmdir src\pytexmk.egg-info /s /q

else
	ifeq ($(UNAME_S),Linux)
		echo "Mac System";
		@rm -fr build/ dist/ src/*.egg-info/
		@find . | grep __pycache__ | xargs rm -fr
		@find . | grep .pyc | xargs rm -f
	else 
		ifeq ($(UNAME_S),Darwin)
		echo "Linux System";
		@rm -rf build/ dist/ src/*.egg-info/
		@find . | grep __pycache__ | xargs rm -rf
		@find . | grep .pyc | xargs rm -f
		endif
	endif
endif

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

inswhl:clean all
	yes | pip uninstall pytexmk
	@pip install dist/*.whl

upload: clean all
	@twine upload dist/*
	@$(MAKE) clean