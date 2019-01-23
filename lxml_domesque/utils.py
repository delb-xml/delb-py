from copy import copy

from lxml import etree


def copy_heading_pis(source: etree._Element, target: etree._Element):
    heading_elements = []
    current_element = source.getprevious()
    while current_element is not None:
        heading_elements.append(current_element)
        current_element = current_element.getprevious()
    while heading_elements:
        target.addprevious(copy(heading_elements.pop()))
