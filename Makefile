all:
	@python -m build


clean:
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	@if exist build rmdir build /s /q
	@if exist dist rmdir dist /s /q
	@if exist "src/pytexmk.egg-info" rmdir "src/pytexmk.egg-info" /s /q

else
ifeq ($(shell uname -s),Linux)
	echo "Linux System";
	@rm -fr build/ dist/ src/*.egg-info/
	@find . | grep __pycache__ | xargs rm -fr
	@find . | grep .pyc | xargs rm -f
else 
ifeq ($(shell uname -s),Darwin)
echo "Mac System";
@rm -rf build/ dist/ src/*.egg-info/
@find . | grep __pycache__ | xargs rm -rf
@find . | grep .pyc | xargs rm -f
endif
endif
	echo "完成清除任务";
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
ifeq ($(shell uname -s),Linux)
	echo "Linux System";
	yes | pip uninstall pytexmk
	@pip install dist/*.whl
	@python tests/test.py -w
	yes | pip uninstall pytexmk
	@$(MAKE) clean
else
ifeq ($(shell uname -s),Darwin)
	echo "Mac System";
	yes | pip uninstall pytexmk
	@pip install dist/*.whl
	@python tests/test.py -w
	yes | pip uninstall pytexmk
	@$(MAKE) clean
endif
endif
	echo "完成测试任务";
endif

inswhl:clean all
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	echo y | pip uninstall pytexmk
	for /r dist %%i in (*.whl) do echo %%i & @pip install "%%~fi"
else
ifeq ($(shell uname -s),Linux)
	echo "Linux System";
	yes | pip uninstall pytexmk
	@pip install dist/*.whl
else 
ifeq ($(shell uname -s),Darwin)
echo "Mac System";
yes | pip uninstall pytexmk
@pip install dist/*.whl
endif
endif
	echo "完成编译安装任务";
endif
	echo "Install pytexmk*.whl file Success";
	
	

upload: clean all
ifeq ($(OS),Windows_NT)
	echo "Windows System";
	echo y | pip uninstall pytexmk
	for /r dist %%i in (*.whl) do echo %%i & @twine upload "%%~fi"
else
ifeq ($(shell uname -s),Linux)
	echo "Linxu System";
	@twine upload dist/*
else 
ifeq ($(shell uname -s),Darwin)
echo "Mac System";
@twine upload dist/*
endif
endif
	echo "完成上传任务";
endif
	
	@$(MAKE) clean
	echo "Upload Success";

pot:
	@xgettext --output=./src/pytexmk/locale/en/main.pot ./src/pytexmk/__main__.py
	@xgettext --output=./src/pytexmk/locale/en/additional.pot ./src/pytexmk/additional_module.py
	@xgettext --output=./src/pytexmk/locale/en/check_version.pot ./src/pytexmk/check_version_module.py
	@xgettext --output=./src/pytexmk/locale/en/compile.pot ./src/pytexmk/compile_module.py
	@xgettext --output=./src/pytexmk/locale/en/config.pot ./src/pytexmk/config_module.py
	@xgettext --output=./src/pytexmk/locale/en/info_print.pot ./src/pytexmk/info_print_module.py
	@xgettext --output=./src/pytexmk/locale/en/latexdiff.pot ./src/pytexmk/latexdiff_module.py
	@xgettext --output=./src/pytexmk/locale/en/logger_config.pot ./src/pytexmk/logger_config.py
	@xgettext --output=./src/pytexmk/locale/en/run.pot ./src/pytexmk/run_module.py
	echo "已生成 pot 文件";

# 作为一名专业的程序国际化专家，请在保留 msgid 中的原文的基础上，将 msgid 中的内容翻译成程序中用的英文，并填写到对应的 msgstr "" 中。
mo:
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/main.mo ./src/pytexmk/locale/en/main.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/additional.mo ./src/pytexmk/locale/en/additional.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/check_version.mo ./src/pytexmk/locale/en/check_version.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/compile.mo ./src/pytexmk/locale/en/compile.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/config.mo ./src/pytexmk/locale/en/config.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/info_print.mo ./src/pytexmk/locale/en/info_print.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/latexdiff.mo ./src/pytexmk/locale/en/latexdiff.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/logger_config.mo ./src/pytexmk/locale/en/logger_config.pot
	@msgfmt -o ./src/pytexmk/locale/en/LC_MESSAGES/run.mo ./src/pytexmk/locale/en/run.pot
	echo "已生成 mo 文件";

poup:

	@xgettext --output=./src/pytexmk/locale/en/main-temp.pot ./src/pytexmk/__main__.py
	@xgettext --output=./src/pytexmk/locale/en/additional-temp.pot ./src/pytexmk/additional_module.py
	@xgettext --output=./src/pytexmk/locale/en/check_version-temp.pot ./src/pytexmk/check_version_module.py
	@xgettext --output=./src/pytexmk/locale/en/compile-temp.pot ./src/pytexmk/compile_module.py
	@xgettext --output=./src/pytexmk/locale/en/config-temp.pot ./src/pytexmk/config_module.py
	@xgettext --output=./src/pytexmk/locale/en/info_print-temp.pot ./src/pytexmk/info_print_module.py
	@xgettext --output=./src/pytexmk/locale/en/latexdiff-temp.pot ./src/pytexmk/latexdiff_module.py
	@xgettext --output=./src/pytexmk/locale/en/logger_config-temp.pot ./src/pytexmk/logger_config.py
	@xgettext --output=./src/pytexmk/locale/en/run-temp.pot ./src/pytexmk/run_module.py

	@msgmerge --update ./src/pytexmk/locale/en/main.pot ./src/pytexmk/locale/en/main-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/additional.pot ./src/pytexmk/locale/en/additional-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/check_version.pot ./src/pytexmk/locale/en/check_version-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/compile.pot ./src/pytexmk/locale/en/compile-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/config.pot ./src/pytexmk/locale/en/config-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/latexdiff.pot ./src/pytexmk/locale/en/latexdiff-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/run.pot ./src/pytexmk/locale/en/run-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/logger_config.pot ./src/pytexmk/locale/en/logger_config-temp.pot
	@msgmerge --update ./src/pytexmk/locale/en/info_print.pot ./src/pytexmk/locale/en/info_print-temp.pot

	@$(MAKE) mo

ifeq ($(OS),Windows_NT)
	echo "Windows System"
	@del ./src/pytexmk/locale/en/main-temp.pot
	@del ./src/pytexmk/locale/en/additional-temp.pot
	@del ./src/pytexmk/locale/en/check_version-temp.pot
	@del ./src/pytexmk/locale/en/compile-temp.pot
	@del ./src/pytexmk/locale/en/config-temp.pot
	@del ./src/pytexmk/locale/en/latexdiff-temp.pot
	@del ./src/pytexmk/locale/en/run-temp.pot
	@del ./src/pytexmk/locale/en/logger_config-temp.pot
	@del ./src/pytexmk/locale/en/info_print-temp.pot
else
ifeq ($(shell uname -s),Linux)
	echo "Linux System"
	@rm ./src/pytexmk/locale/en/main-temp.pot
	@rm ./src/pytexmk/locale/en/additional-temp.pot
	@rm ./src/pytexmk/locale/en/check_version-temp.pot
	@rm ./src/pytexmk/locale/en/compile-temp.pot
	@rm ./src/pytexmk/locale/en/config-temp.pot
	@rm ./src/pytexmk/locale/en/latexdiff-temp.pot
	@rm ./src/pytexmk/locale/en/run-temp.pot
	@rm ./src/pytexmk/locale/en/logger_config-temp.pot
	@rm ./src/pytexmk/locale/en/info_print-temp.pot
endif
ifeq ($(shell uname -s),Darwin)
	echo "Mac System"
	@rm ./src/pytexmk/locale/en/main-temp.pot
	@rm ./src/pytexmk/locale/en/additional-temp.pot
	@rm ./src/pytexmk/locale/en/check_version-temp.pot
	@rm ./src/pytexmk/locale/en/compile-temp.pot
	@rm ./src/pytexmk/locale/en/config-temp.pot
	@rm ./src/pytexmk/locale/en/latexdiff-temp.pot
	@rm ./src/pytexmk/locale/en/run-temp.pot
	@rm ./src/pytexmk/locale/en/logger_config-temp.pot
	@rm ./src/pytexmk/locale/en/info_print-temp.pot
endif
	echo "已完成国际化文件更新";
endif