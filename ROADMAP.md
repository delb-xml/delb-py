# Roadmap for delb-py

## 0.6

- a native implementation of the data model
- add a node type for CDATA
- move parsing to a separate module with a dummy parser that still uses lxml as backend
- provide means to build a wheel with *mypyc*
  - but don't publish a mypycified wheel yet

## 0.7

- a native XML parser
- re-add the argument `parser` for `delb.Document`
- deprecate `parser_options` of `delb.Document`
- make `_delb.plugins.core_loaders.etree_loader` an extra option

## 0.8

- drop any remaining checks against lxml equivalents
- remove all remaining deprecated features
- performance optimizations
