# Copyright (C) 2018-'25  Frank Sachsenheim
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

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from _delb.plugins import plugin_manager
from _delb.typing import TagNodeType, TextNodeType

if TYPE_CHECKING:
    from _delb.xpath.ast import EvaluationContext


@plugin_manager.register_xpath_function
def concat(_: EvaluationContext, *strings: str) -> str:
    return "".join(strings)


@plugin_manager.register_xpath_function
def contains(_: EvaluationContext, string: str, substring: str) -> bool:
    return substring in string


@plugin_manager.register_xpath_function
def boolean(_: EvaluationContext, value: Any) -> bool:
    return bool(value)


@plugin_manager.register_xpath_function
def last(context: EvaluationContext) -> int:
    return context.size


@plugin_manager.register_xpath_function("not")
def _not(_: EvaluationContext, value: Any) -> bool:
    return not value


@plugin_manager.register_xpath_function
def position(context: EvaluationContext) -> int:
    return context.position


@plugin_manager.register_xpath_function("starts-with")
def starts_with(_: EvaluationContext, string: str, prefix: str) -> bool:
    return string.startswith(prefix)


@plugin_manager.register_xpath_function
def text(context: EvaluationContext) -> str:
    assert isinstance(context.node, TagNodeType)
    for node in context.node._child_nodes:
        if isinstance(node, TextNodeType):
            break
    else:
        return ""
    return node.content
