default: tests


version := `hatch version`

_assert_no_dev_version:
  #!/usr/bin/env python3
  if "dev" in "{{version}}":
    raise SystemExit(1)

# run benchmarks
benchmarks:
    hatch run benchmarks:run

# normalize Python code
black:
    black benchmarks _delb delb integration-tests tests

# runs tests (except loaders) and reports uncovered lines
coverage-report:
    hatch run unit-tests:coverage-report

# code linting with flake8
code-lint:
    hatch run linting:check

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

# run the complete testsuite
pytest:
    hatch run unit-tests:check

# release the current version on github & (transitively) the PyPI
release: _assert_no_dev_version tests
    {{just_executable()}} -f {{justfile()}} update-citation-file
    git add CITATION.cff
    git commit -m "Updates CITATION.cff"
    git tag {{version}}
    git push origin main
    git push origin {{version}}

# watch, build and serve HTML documentation at 0.0.0.0:8000
serve-docs:
    hatch run docs:serve

# build and open HTML documentation
show-docs: docs
    xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: black code-lint mypy pytest doctest

# run the testsuite against a wheel (installed from $WHEEL_PATH); intended to run on a CI platform
test-wheel $WHEEL_PATH:
    hatch run test-wheel:check

# Generates and validates CITATION.cff
update-citation-file:
    hatch run citation-file:cff-from-621
