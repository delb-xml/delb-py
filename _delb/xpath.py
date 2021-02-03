# Copyright (C) 2018-'21  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from typing import List


AXIS_NAMES = (
    "ancestor",
    "ancestor-or-self",
    "attribute",
    "child",
    "descendant",
    "descendant-or-self",
    "following",
    "following-sibling",
    "namespace",
    "parent",
    "preceding",
    "preceding-sibling",
    "self",
)


class XPathExpression:
    def __init__(self, expression: str):
        self.location_paths = [LocationPath(x.strip()) for x in expression.split("|")]

    def __str__(self):
        return " | ".join(str(x) for x in self.location_paths)


class LocationPath:
    def __init__(self, expression: str):
        self.location_steps = [LocationStep(x) for x in expression.split("/")]

    def __str__(self):
        return "/".join(str(x) for x in self.location_steps)


class LocationStep:
    def __init__(self, expression: str):
        self.axis: str
        self.node_test: NodeTest
        self.predicates: List[Predicate] = []

        if expression == "":
            self.axis = "descendant-or-self"
            self.node_test = NodeTest("node()")
        elif expression == ".":
            self.axis = "self"
            self.node_test = NodeTest("node()")
        elif expression == "..":
            self.axis = "parent"
            self.node_test = NodeTest("node()")
        else:
            if "[" in expression:
                expression, predicates_part = expression.split("[", maxsplit=1)
                assert predicates_part[-1] == "]", predicates_part
                self.predicates = [
                    Predicate(x) for x in predicates_part[:-1].split("][")
                ]

            if expression.startswith("@"):
                expression = "attribute::" + expression[1:]

            if "::" not in expression:
                self.axis = "child"
                self.node_test = NodeTest(expression)
            else:
                self.axis, node_test_part = expression.split("::")
                self.node_test = NodeTest(node_test_part)

        if self.axis not in AXIS_NAMES:
            raise ValueError(f"`{self.axis}` is not a valid axis name.")

    def __str__(self):
        return (
            self.axis
            + "::"
            + str(self.node_test)
            + "".join(str(x) for x in self.predicates)
        )


class NodeTest:
    def __init__(self, expression: str):
        self.data = expression

        if expression.endswith(")"):
            self.type = "type_test"
        else:
            self.type = "name_test"

    def __str__(self):
        return self.data


class Predicate:
    def __init__(self, expression: str):
        self.expression = expression

    def __str__(self):
        return "[" + self.expression + "]"
