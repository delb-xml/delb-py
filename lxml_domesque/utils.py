from copy import copy
from string import ascii_lowercase
from functools import lru_cache

from cssselect import GenericTranslator  # type: ignore
from lxml import etree


css_translator = GenericTranslator()


def copy_heading_pis(source: etree._Element, target: etree._Element):
    heading_elements = []
    current_element = source.getprevious()
    while current_element is not None:
        heading_elements.append(current_element)
        current_element = current_element.getprevious()
    while heading_elements:
        target.addprevious(copy(heading_elements.pop()))


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
