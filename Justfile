# this file is be used for evaluation of an alternative to Makefile
# see https://github.com/casey/just for details

default: tests


citation_template := `cat CITATION.cff.tmpl`
date := `date '+%Y-%m-%d'`
version := `poetry version --short`


# run benchmarks
benchmarks:
    python -m pytest --benchmark-autosave --benchmark-group-by=name --benchmark-timer=time.process_time benchmarks

# normalize Python code
black:
    black benchmarks _delb delb tests

# generate Sphinx HTML documentation, including API docs
docs:
	make -C docs clean
	make -C docs html

# code linting with black & flake8
check-formatting:
	black --check benchmarks _delb delb tests
	flake8 benchmarks _delb delb tests

# test the code that is contained in the docs
doctest:
	make -C docs doctest

# run static type checks with mypy
mypy:
	mypy _delb delb

# run most of the test suite, avoid network
pytest:
	python -m pytest tests

# run the complete testsuite
pytest-all:
    TEST_LOADERS=1 python -m pytest --cov=_delb --cov=delb tests

# release the current version on github & the PyPI
release: tests
    test "{{trim_end_match(version, '-dev')}}" = "{{version}}" || false
    {{just_executable()}} -f {{justfile()}} update-citation-file
    git add CITATION.cff
    git commit -m "Updates CITATION.cff"
    git tag -f {{version}}
    git push origin main
    git push -f origin {{version}}
    poetry publish --build

# build and open HTML documentation
showdocs: docs
    xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: black check-formatting mypy pytest-all doctest
    poetry check

# Generates and validates CITATION.cff
update-citation-file:
    @echo "{{ replace(replace(citation_template, "_DATE_", date), "_VERSION_", version) }}" > CITATION.cff
    cffconvert --validate
