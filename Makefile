.DEFAULT_GOAL := tests

.PHONY: black
black:
	black lxml_domesque tests

.PHONY: pytest
pytest:
	python -m pytest tests

.PHONY: tests
tests: black pytest
