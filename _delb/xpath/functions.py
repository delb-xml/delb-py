# Copyright (C) 2018-'22  Frank Sachsenheim
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

from typing import TYPE_CHECKING, Any, Callable, Union

if TYPE_CHECKING:
    from _delb.xpath.ast import EvaluationContext


xpath_functions = {}


# TODO move to PluginManager
def register_xpath_function(arg: Union[Callable, str]) -> Callable:
    """TODO"""
    if isinstance(arg, str):

        def wrapper(func):
            xpath_functions[arg] = func
            return func

        return wrapper

    if callable(arg):
        xpath_functions[arg.__name__] = arg
        return arg


@register_xpath_function
def concat(*strings: str) -> str:
    return "".join(strings)


@register_xpath_function
def contains(_, string: str, substring: str) -> bool:
    return substring in string


@register_xpath_function
def boolean(_, value: Any) -> bool:
    return bool(value)


@register_xpath_function
def last(context: EvaluationContext) -> int:
    return context.size


@register_xpath_function("not")
def _not(_, value: Any) -> bool:
    return not value


@register_xpath_function
def position(context: EvaluationContext) -> int:
    return context.position


@register_xpath_function("starts-with")
def starts_with(_, string: str, prefix: str) -> bool:
    return string.startswith(prefix)
