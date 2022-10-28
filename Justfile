# this file is be used for evaluation of an alternative to Makefile
# see https://github.com/casey/just for details

default: tests


citation_template := `cat CITATION.cff.tmpl`
date := `date '+%Y-%m-%d'`
version := `hatch version`


# run benchmarks
benchmarks:
    hatch run benchmarks:run

# normalize Python code
black:
    black benchmarks _delb delb tests

# code linting with black & flake8
check-formatting:
    hatch run linting:check

# runs tests (except loaders) and reports uncovered lines
coverage-report:
    hatch run unit-tests:coverage-report

# generate Sphinx HTML documentation, including API docs
docs:
    hatch run docs:clean
    hatch run docs:build-html

# verifies testable code snippets in the HTML documentation
doctest:
    hatch run docs:clean
    hatch run docs:doctest

# run static type checks with mypy
mypy:
    hatch run mypy:check

# run most of the test suite, avoid network
pytest:
    hatch run unit-tests:check

# run the complete testsuite
pytest-all:
    TEST_LOADERS=1 hatch run unit-tests:check

# release the current version on github & the PyPI
release: tests
    test "{{trim_end_match(version, '-dev')}}" = "{{version}}" || false
    {{just_executable()}} -f {{justfile()}} update-citation-file
    git add CITATION.cff
    git commit -m "Updates CITATION.cff"
    git tag -f {{version}}
    git push origin main
    git push -f origin {{version}}
    hatch clean
    hatch build
    hatch publish

# build and open HTML documentation
showdocs: docs
    xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: black check-formatting mypy pytest-all doctest

# Generates and validates CITATION.cff
update-citation-file:
    @echo "{{ replace(replace(citation_template, "_DATE_", date), "_VERSION_", version) }}" > CITATION.cff
    cffconvert --validate
