# Roadmap for delb-py

## 0.6

- move `_delb.parser.ParserOptions` to the `delb.parser` package
- remove `_delb.TagNode.parse`
- provide a `delb.parser.parse` function as replacement, re-expose it in the `delb`
  module
- how should the otherwise equivalent function to parse a node sequence be called?
    - or explicity `parse_one_node` and `parse_multiple_nodes`?
- the tree building will be based on (SaX-like) event parsers for which a common
  abstract interface needs to be defined, considering concrete implementations of
  adapters for:
    - `lxml.etree.XMLPullParser`
    - `xml.sax`
    - possibly a Python wrapper for https://crates.io/crates/xmlparser in a separate
      package
    - maybe even a `re` based one for platforms where none of the above is available
- what should be defined as common behaviour configuration options?
    - except `resolve_entities` the current ones of `ParserOptions` are fine as such imo
- CDATA will be parsed to text nodes
- move parsing from loaders to the `Document` class, thus breaking their interface
    - they're then supposed to return a file-like object
- remove `_delb.plugins.core_loaders.etree_loader`
    - if lxml objects as input is a future use-case, a conversion should be maintained
      in a separate package

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
