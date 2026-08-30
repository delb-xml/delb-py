set unstable := true # for set lists
set lists := true # for which()

black := which(["black"]) || "pipx run black"
hatch := which(["hatch"]) || "pipx run hatch"
version := f'{{hatch}} version'

default: check

_assert_no_dev_version:
    #!/usr/bin/env python3
    if "dev" in "{{ version }}":
      raise SystemExit(1)

# run benchmarks
benchmarks:
    {{ hatch }} run benchmarks:run

# normalize Python code
black:
    {{ black }} benchmarks _delb delb tests update-reexports.py

# runs tests on normalized code
check: update-reexports black tests

# generate Sphinx HTML documentation, including API docs
docs:
    {{ hatch }} run docs:clean
    {{ hatch }} run docs:build-html

# verifies testable code snippets in the HTML documentation
doctest:
    {{ hatch }} run docs:clean
    {{ hatch }} run docs:doctest

# various linters
[parallel]
lint: lint-code lint-rst lint-yaml

# code linting with flake8
lint-code:
    {{ hatch }} run linting:check

# .rst linting with doc8
lint-rst:
    pipx run doc8 --ignore-path docs/build --max-line-length=80 docs

# yaml linting with yamllint
lint-yaml:
    pipx run yamllint $(find . -name "*.yaml" -or -name "*.yml")

# run static type checks with mypy
mypy:
    {{ hatch }} run mypy:check

# run the complete testsuite
pytest:
    {{ hatch }} run unit-tests:check

# release the current version on github & (transitively) the PyPI
release: _assert_no_dev_version check
    {{ just_executable() }} -f {{ justfile() }} update-citation-file
    git add CITATION.cff
    git commit -m "Updates CITATION.cff"
    git tag {{ version }}
    git push origin main
    git push origin {{ version }}

# watch, build and serve HTML documentation at 0.0.0.0:8000
serve-docs:
    mkdir -p {{ justfile_directory() }}/docs/build/html || true
    {{ hatch }} run docs:serve

# build and open HTML documentation
show-docs: docs
    xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: lint mypy pytest doctest

# run the testsuite against a wheel (installed from $WHEEL_PATH); intended to run on a CI platform
test-wheel $WHEEL_PATH:
    {{ hatch }} run test-wheel:check

# generates and validates CITATION.cff
update-citation-file:
    pipx run cff-from-621

# updates re-exports in the delb package
update-reexports:
    python {{ justfile_directory() }}/update-reexports.py
