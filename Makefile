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

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: mypy
mypy: ## run static type checks with mypy
	mypy lxml_domesque

.PHONY: pytest
pytest: ## run the test suite
	python -m pytest tests

.PHONY: tests ## run all tests on normalized code
tests: black mypy pytest
