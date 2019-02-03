.DEFAULT_GOAL := tests


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
	black lxml_domesque tests

.PHONY: black-check
black-check: ## check whether Python code is normalized
	black --check --diff lxml_domesque tests

.PHONY: check-style
check-style: black-check flake8 ## checks the code style

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: flake8
flake8: ## code linting with flake8
	flake8 lxml_domesque tests

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: mypy
mypy: ## run static type checks with mypy
	MYPYPATH=./lxml-stubs mypy lxml_domesque

.PHONY: pytest
pytest: ## run the test suite
	python -m pytest --cov-config .coveragerc --cov=lxml_domesque tests

.PHONY: tests ## run all tests on normalized code
tests: black flake8 mypy pytest
