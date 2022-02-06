#!/usr/bin/env python3.8
# @generated by pegen from _delb/xpath/xpath.gram

import ast
import sys
import tokenize

from typing import Any, Optional

from pegen.parser import memoize, memoize_left_rec, logger, Parser

from _delb.xpath.ast import *

# Keywords and soft keywords are listed at the end of the parser definition.
class XPathParser(Parser):
    @memoize
    def start(self) -> Optional[Any]:
        # start: "|".location_path+
        mark = self._mark()
        if paths := self._gather_1():
            return XPathExpression(paths)
        self._reset(mark)
        return None

    @memoize
    def location_path(self) -> Optional[Any]:
        # location_path: "/".location_step+
        mark = self._mark()
        if steps := self._gather_3():
            return LocationPath(steps)
        self._reset(mark)
        return None

    @memoize
    def location_step(self) -> Optional[Any]:
        # location_step: name_test
        mark = self._mark()
        if name_test := self.name_test():
            return LocationStep(name_test)
        self._reset(mark)
        return None

    @memoize
    def name_test(self) -> Optional[Any]:
        # name_test: NAME | "."
        mark = self._mark()
        if pattern := self.name():
            return NameTest(pattern)
        self._reset(mark)
        if pattern := self.expect("."):
            return NameTest(".")
        self._reset(mark)
        return None

    @memoize
    def _loop0_2(self) -> Optional[Any]:
        # _loop0_2: "|" location_path
        mark = self._mark()
        children = []
        while (literal := self.expect("|")) and (elem := self.location_path()):
            children.append(elem)
            mark = self._mark()
        self._reset(mark)
        return children

    @memoize
    def _gather_1(self) -> Optional[Any]:
        # _gather_1: location_path _loop0_2
        mark = self._mark()
        if (elem := self.location_path()) is not None and (
            seq := self._loop0_2()
        ) is not None:
            return [elem] + seq
        self._reset(mark)
        return None

    @memoize
    def _loop0_4(self) -> Optional[Any]:
        # _loop0_4: "/" location_step
        mark = self._mark()
        children = []
        while (literal := self.expect("/")) and (elem := self.location_step()):
            children.append(elem)
            mark = self._mark()
        self._reset(mark)
        return children

    @memoize
    def _gather_3(self) -> Optional[Any]:
        # _gather_3: location_step _loop0_4
        mark = self._mark()
        if (elem := self.location_step()) is not None and (
            seq := self._loop0_4()
        ) is not None:
            return [elem] + seq
        self._reset(mark)
        return None

    KEYWORDS = ()
    SOFT_KEYWORDS = ()
