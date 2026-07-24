# PyTeXMK unified build & development entry point
#
# Usage (requires GNU Make and uv):
#   make help          Show all available targets
#   make install       Install dependencies with uv
#   make test          Run unit tests
#   make lint          Run ruff linter
#   make format        Run ruff formatter
#   make build         Build wheel + sdist
#   make build-exe     Build PyInstaller onedir
#   make clean         Clean build artifacts
#   make dist          Build full distribution
#   make ci-test       CI pipeline (lint + test)
#   make pot           Generate .pot translation templates
#   make mo            Compile .pot to .mo files
#   make i18n-update   Update translations (pot + mo)
#   make html          Generate README.html from README.md
#
# Windows users without Make can use:
#   uv run python tools/make.py <target>

PYTHON ?= uv run python
MAKE_SCRIPT := tools/make.py

.PHONY: help all clean install install-dev test test-cov test-integration \
        lint lint-fix format format-check build build-exe build-exe-onefile \
        install-pkg uninstall-pkg inswhl pot mo i18n-update poup html version dist \
        ci-test ci-full publish-tag

help:
	@$(PYTHON) $(MAKE_SCRIPT) help

all: ci-full

clean:
	@$(PYTHON) $(MAKE_SCRIPT) clean

install:
	@$(PYTHON) $(MAKE_SCRIPT) install

install-dev:
	@$(PYTHON) $(MAKE_SCRIPT) install-dev

test:
	@$(PYTHON) $(MAKE_SCRIPT) test

test-cov:
	@$(PYTHON) $(MAKE_SCRIPT) test-cov

test-integration:
	@$(PYTHON) $(MAKE_SCRIPT) test-integration

lint:
	@$(PYTHON) $(MAKE_SCRIPT) lint

lint-fix:
	@$(PYTHON) $(MAKE_SCRIPT) lint-fix

format:
	@$(PYTHON) $(MAKE_SCRIPT) format

format-check:
	@$(PYTHON) $(MAKE_SCRIPT) format-check

build:
	@$(PYTHON) $(MAKE_SCRIPT) build

build-exe:
	@$(PYTHON) $(MAKE_SCRIPT) build-exe

build-exe-onefile:
	@$(PYTHON) $(MAKE_SCRIPT) build-exe-onefile

install-pkg:
	@$(PYTHON) $(MAKE_SCRIPT) install-pkg

uninstall-pkg:
	@$(PYTHON) $(MAKE_SCRIPT) uninstall-pkg

inswhl:
	@$(PYTHON) $(MAKE_SCRIPT) inswhl

pot:
	@$(PYTHON) $(MAKE_SCRIPT) pot

mo:
	@$(PYTHON) $(MAKE_SCRIPT) mo

i18n-update:
	@$(PYTHON) $(MAKE_SCRIPT) i18n-update

poup:
	@$(PYTHON) $(MAKE_SCRIPT) poup

html:
	@$(PYTHON) $(MAKE_SCRIPT) html

version:
	@$(PYTHON) $(MAKE_SCRIPT) version

dist:
	@$(PYTHON) $(MAKE_SCRIPT) dist

ci-test:
	@$(PYTHON) $(MAKE_SCRIPT) ci-test

ci-full:
	@$(PYTHON) $(MAKE_SCRIPT) ci-full

publish-tag:
	@$(PYTHON) $(MAKE_SCRIPT) publish-tag
