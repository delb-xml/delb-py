# Roadmap for delb-py

## 0.4

- all currently planned changes
  - [here](https://github.com/delb-xml/delb-py/milestone/4)
  - [and here](https://github.com/delb-xml/delb-py/milestone/3)
- deprecate these features provided by *lxml*:
  - `delb.Document.xslt`
    - such feature would have to be implemented in a separate package
  - `_delb.utils.register_namespace`
    - to be functionally replaced with `namespace_declarations` on `TagNode` instances
  - `_delb.plugins.http_ftp_loader`
    - the `_delb.plugins.https_loader.https_loader` becomes `.we_get_requests.http_s_loader`
  - ? what about the `_delb.plugins.core_loaders.tag_node_loader` and `.etree_loader` ?
    - if that functionality shall be kept, then as optional
  - the `parser` and `collapse_whitespace` argument to a `delb.Document`
    - instead a `parser_options` argument is added that allows these arguments (for `lxml.etree.XMLParser` equivalents):
      - `cleanup_namespaces` (`ns_clean`)
      - `collapse_whitespace`
      - `remove_nodes_of_type`, a container with subclasses of `NodeBase` (*various*)
      - `resolve_entities` (*dito*)
        - later to be replaced with more specific control
      - `unplugged` (`no_network`)
- include a first set of benchmarks

## 0.5

- a native implementation of data serialization
  - compared against lxml's production when running in unoptimized Python level
  - while figuring out [modes to deal with whitespace](https://github.com/delb-xml/delb-py/issues/54)

## 0.6

- a native implementation of the data model
- add a node type for CDATA
- move parsing to a separate module with a dummy that still uses lxml as backend
- provide means to build a wheel with *mypyc*
- don't publish any wheel of this version

## 0.7

- a native XML parser
- re-add the argument `parser` for `delb.Document`
- deprecate `parser_options` of `delb.Document`

## 0.8

- performance optimizations
- drop any remaining checks against lxml equivalents
