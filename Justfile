default: tests


version := `pipx run hatch version`

_assert_no_dev_version:
  #!/usr/bin/env python3
  if "dev" in "{{version}}":
    raise SystemExit(1)

# run benchmarks
benchmarks:
    pipx run hatch run benchmarks:run

# normalize Python code
black:
    pipx run black benchmarks _delb delb tests

# runs tests and reports coverage
coverage-report:
    pipx run hatch run unit-tests:coverage-report

# generate Sphinx HTML documentation, including API docs
docs:
    pipx run hatch run docs:clean
    pipx run hatch run docs:build-html

# verifies testable code snippets in the HTML documentation
doctest:
    pipx run hatch run docs:clean
    pipx run hatch run docs:doctest

# code & data & document linting with doc8 & flake8 & yamllint
lint:
    pipx run doc8 --ignore-path docs/build --max-line-length=80 docs
    pipx run hatch run linting:check
    pipx run yamllint $(find . -name "*.yaml" -or -name "*.yml")

# run static type checks with mypy
mypy:
    pipx run hatch run mypy:check

# run the complete testsuite
pytest:
    pipx run hatch run unit-tests:check

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
    mkdir -p {{ justfile_directory() }}/docs/build/html || true
    pipx run hatch run docs:serve

# build and open HTML documentation
show-docs: docs
    xdg-open docs/build/html/index.html

# run all tests on normalized code
tests: black lint mypy pytest doctest

# run the testsuite against a wheel (installed from $WHEEL_PATH); intended to run on a CI platform
test-wheel $WHEEL_PATH:
    pipx run hatch run test-wheel:check

# Generates and validates CITATION.cff
update-citation-file:
    pipx run cff-from-621
