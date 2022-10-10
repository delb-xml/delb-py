# Roadmap for delb-py

## 0.4

- all currently planned changes [here](https://github.com/delb-xml/delb-py/milestone/3)

## 0.5

- a native implementation of data serialization
  - compared against lxml's production when running in unoptimized Python level
  - while figuring out [modes to deal with whitespace](https://github.com/delb-xml/delb-py/issues/54)

## 0.6

- a native implementation of the data model
- add a node type for CDATA
- move parsing to a separate module with a dummy parser that still uses lxml as backend
- provide means to build a wheel with *mypyc*
- don't publish any wheel of this version

## 0.7

- a native XML parser
- re-add the argument `parser` for `delb.Document`
- deprecate `parser_options` of `delb.Document`
- make `_delb.plugins.core_loaders.tag_node_loader` and `.etree_loader` an extra option

## 0.8

- drop any remaining checks against lxml equivalents
- remove all remaining deprecated features
- performance optimizations
