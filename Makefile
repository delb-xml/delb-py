.DEFAULT_GOAL := tests

VERSION = $(shell grep -oP "^version = \K.+" pyproject.toml)
# mind that the result includes surrounding quotes


define PRINT_HELP_PYSCRIPT
import re, sys
for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT


.PHONY: black
black: ## normalize Python code
	black _delb delb tests

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

.PHONY: doctest
doctest: ## test the code that is contained in the docs
	$(MAKE) -C docs doctest

.PHONY: flake8
flake8: ## code linting with flake8
	flake8 _delb delb tests

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: mypy
mypy: ## run static type checks with mypy
	MYPYPATH=./lxml-stubs mypy _delb delb

.PHONY: pytest
pytest: ## run the test suite
	python -m pytest --cov-config .coveragerc --cov=_delb --cov=delb tests

.PHONY: release
release: tests ## release the current version on github & the PyPI
	git tag -f $(VERSION)
	git push origin master
	git push -f origin $(VERSION)
	poetry publish --build

.PHONY: showdocs
showdocs: docs ## build and open HTML documentation
	xdg-open docs/build/html/index.html

.PHONY: tests ## run all tests on normalized code
tests: black flake8 mypy pytest doctest
	poetry check
