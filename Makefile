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