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
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	echo y | pip uninstall pytexmk
	for /r dist %%i in (*.whl) do echo %%i & @pip install "%%~fi"
	@python tests/test.py -w
	echo y | pip uninstall pytexmk
	@$(MAKE) clean
else
	ifeq ($(UNAME_S),Linux)
		echo "Linux System";
		yes | pip uninstall pytexmk
		@pip install dist/*.whl
		@python tests/test.py -w
		yes | pip uninstall pytexmk
		@$(MAKE) clean
	else
		ifeq ($(UNAME_S),Darwin)
			echo "Mac System";
			yes | pip uninstall pytexmk
			@pip install dist/*.whl
			@python tests/test.py -w
			yes | pip uninstall pytexmk
			@$(MAKE) clean
		endif
	endif
endif

inswhl:clean all
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	echo y | pip uninstall pytexmk
	for /r dist %%i in (*.whl) do echo %%i & @pip install "%%~fi"
else
	ifeq ($(UNAME_S),Linux)
		echo "Mac System";
		yes | pip uninstall pytexmk
		@pip install dist/*.whl
	else 
		ifeq ($(UNAME_S),Darwin)
		echo "Linux System";
		yes | pip uninstall pytexmk
		@pip install dist/*.whl
		endif
	endif
endif
	echo "Install pytexmk*.whl file Success";
	
	

upload: clean all
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	echo y | pip uninstall pytexmk
	for /r dist %%i in (*.whl) do echo %%i & @twine upload "%%~fi"
else
	ifeq ($(UNAME_S),Linux)
		echo "Mac System";
		@twine upload dist/*
	else 
		ifeq ($(UNAME_S),Darwin)
		echo "Linux System";
		@twine upload dist/*
		endif
	endif
endif
	
	@$(MAKE) clean
	echo "Upload Success";