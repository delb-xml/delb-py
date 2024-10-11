import os
import posixpath
import sys
from pathlib import Path

from panflute import run_filter, Code, Link, Str
from sphinx.util.inventory import InventoryFile


BASE_URL = os.environ["DELB_DOCS_BASE_URL"]
CWD = Path.cwd()
ROLES_MAPPING = {
    "attr": "py:attribute",
    "class": "py:class",
    "doc": "std:doc",
    # ?"exception"?: "py:exception",
    "func": "py:function",
    "meth": "py:method",
    "mod": "py:module",
    # ???: "py:property",
    "term": "std:term",
}


def bend_links(elem, doc):
    if not (isinstance(elem, Code) and "interpreted-text" in elem.classes):
        return elem

    inventory_section = ROLES_MAPPING[elem.attributes["role"]]
    target = doc.inventory[inventory_section].get(elem.text)

    if target is None:
        # this is okay for non-existing entries such as :meth:`NodeBase.…` and
        # objects in other inventories like Python's docs
        print(f"WARNING: No inventory object for '{elem.text}' found.", file=sys.stderr)
        return Code(elem.text)

    if (label_text := target[3]) == "-":
        label_text = elem.text

    if inventory_section.startswith("py:"):
        label = Code(label_text)
    else:
        label = Str(f"„{label_text}”")

    return Link(label, url=target[2])


def prepare(doc):
    with (CWD / "docs" / "build" / "html" / "objects.inv").open("rb") as f:
        doc.inventory = InventoryFile.load(f, BASE_URL, posixpath.join)


def main(doc=None):
    return run_filter(bend_links, prepare=prepare)


if __name__ == "__main__":
    main()
