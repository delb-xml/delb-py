# Integration tests against corpora

This folder serves as playground for tests of basic functionality against many
XML documents, mostly TEI-encodings. They are supposed to be executed with
major code change proposals and before releases.

## Test corpus

Place document collections into the `corpora` folder. The `fetch-corpora.py`
script helps to get going with the minimal requirement (~3GB) of tests.

Due to the `lb` tag [issue](https://github.com/deutschestextarchiv/dtabf/issues/33)
with the DTABf the DTA corpus isn't considered. It could be an experiment to
use *delb* for transformations with regards to the conclusions of that issue.

The `normalize-corpora.py` script addresses issues that were found in the text
encodings and must be run before the tests.

## Tests

These are contained in the scripts named `test-*.py`.

The scripts write occasional progress indicators to *stderr*. The `.gitignore`
reserves a `report.txt` for messages redirected from *stdout*.

When problems occur, carefully investigate that it's not due to the source, and
if not extract simple enough cases for the unit tests.
