all:
	@python ./tools/make.py all

clean:
	@python ./tools/make.py clean

html:
	@python ./tools/make.py html

rst:
	@python ./tools/make.py rst

test:
	@python ./tools/make.py test

testwhl:
	@python ./tools/make.py testwhl

inswhl:
	@python ./tools/make.py inswhl

upload:
	@python ./tools/make.py upload

pot:
	@python ./tools/make.py pot

mo:
	@python ./tools/make.py mo

poup:
	@python ./tools/make.py poup

# 作为一名专业的程序国际化专家，请在保留 msgid 中的原文的基础上，将 msgid 中的内容翻译成程序中用的英文，并填写到对应的 msgstr "" 中
# 国际化更新流程：首先 运行 poup，然后修改pot文件，随后 运行 mo，删掉多余文件即可