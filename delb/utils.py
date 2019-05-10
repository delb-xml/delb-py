# Copyright (C) 2019  Frank Sachsenheim
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


from copy import copy
from string import ascii_lowercase
from functools import lru_cache

from cssselect import GenericTranslator  # type: ignore
from lxml import etree


css_translator = GenericTranslator()


def copy_root_siblings(source: etree._Element, target: etree._Element):
    stack = []
    current_element = source.getprevious()
    while current_element is not None:
        stack.append(current_element)
        current_element = current_element.getprevious()
    while stack:
        target.addprevious(copy(stack.pop()))

    stack = []
    current_element = source.getnext()
    while current_element is not None:
        stack.append(current_element)
        current_element = current_element.getnext()
    while stack:
        target.addnext(copy(stack.pop()))


# TODO make cachesize configurable via environment variable?
@lru_cache(maxsize=64)
def css_to_xpath(expression: str) -> str:
    return css_translator.css_to_xpath(expression, prefix="descendant-or-self::")


def random_unused_prefix(namespaces: "etree._NSMap") -> str:
    for prefix in ascii_lowercase:
        if prefix not in namespaces:
            return prefix
    raise RuntimeError(
        "You really are using all latin letters as prefix in a document. "
        "Fair enough, please open a bug report."
    )
