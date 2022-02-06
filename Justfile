# this file is be used for evaluation of an alternative to Makefile
# see https://github.com/casey/just for details

default: tests


version := `poetry version --short`


# normalize Python code
black:
    black _delb delb tests

# generate Sphinx HTML documentation, including API docs
docs:
	make -C docs clean
	make -C docs html

# code linting with black & flake8
check-formatting:
	black --check _delb delb tests
	flake8 _delb delb tests

# test the code that is contained in the docs
doctest:
	make -C docs doctest

# generate the XPath parser module
generate-xpath-parser:
    python -m pegen _delb/xpath/xpath.gram -o _delb/xpath/parser.py

# run static type checks with mypy
mypy:
	mypy _delb delb

# run the test suite
pytest:
	python -m pytest --cov-config .coveragerc --cov=_delb --cov=delb tests

# release the current version on github & the PyPI
release: tests
	git tag -f {{version}}
	git push origin main
	git push -f origin {{version}}
	poetry publish --build

# build and open HTML documentation
showdocs: docs
	xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: black check-formatting mypy pytest doctest
	poetry check
