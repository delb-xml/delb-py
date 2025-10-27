# Roadmap for delb-py

## 0.7

- provide means to build a wheel with *mypyc*
- declare the API as stable, from now on new features should be released under
  a "preview" notion

## 0.8

- remove all remaining deprecated features
- performance optimizations

## 0.9

- a proper serialization implementation with focus on performance and possibly
  extendability

## unscheduled

- a general query interface
  - with some simple/performant queries (find[_following|preceding] based on names
    and/or attributes)
  - translation of XPathExpressions to such when applicable
- an independent parser implementation
  - without any DTD support
- inclusion of a RelaxNG validator
  - grown in an extra package
