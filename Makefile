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
#
# Windows users without Make can use:
#   uv run python tools/make.py <target>

PYTHON ?= uv run python
MAKE_SCRIPT := tools/make.py

.PHONY: help all clean install install-dev test test-cov test-integration \
        lint lint-fix format format-check build build-exe build-exe-onefile \
        install-pkg uninstall-pkg pot mo i18n-update version dist \
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

pot:
	@$(PYTHON) $(MAKE_SCRIPT) pot

mo:
	@$(PYTHON) $(MAKE_SCRIPT) mo

i18n-update:
	@$(PYTHON) $(MAKE_SCRIPT) i18n-update

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
