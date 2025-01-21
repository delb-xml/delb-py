# Roadmap for delb-py

## 0.6

- the tree building will be based on (SaX-like) event parsers for which a common
  abstract interface needs to be defined, considering concrete implementations of
  adapters for:
    - possibly a Python wrapper for https://crates.io/crates/xmlparser in a separate
      package
    - maybe even a `re` based one for platforms where none of the above is available
- what should be defined as common behaviour configuration options?
    - except `resolve_entities` the current ones of `ParserOptions` are fine as such imo
- CDATA will be parsed to text nodes

## 0.7

- drop support for eol'ed Python versions
- a native implementation of the data model
- declare the API as mostly stable

## 0.8

- provide means to build a wheel with *mypyc*
- declare the API as stable, from now on new features should be released under
  a "preview" notion

## 0.9

- drop any remaining checks against lxml equivalents
- remove all remaining deprecated features
- performance optimizations

## 0.10

- a proper serialization implementation with focus on performance and possibly
  extendability
