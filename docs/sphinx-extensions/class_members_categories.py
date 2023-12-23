from abc import ABC
import re


def setup(app):
    app.setup_extension("autodocsumm")
    app.connect("autodocsumm-grouper", assign_member_category)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        # this is not based on information, it's guessed:
        "parallel_write_safe": True,
    }


match_category = re.compile(r"\s*:meta category: ([a-zA-Z -]+[a-z])\s*").match


def assign_member_category(app, what, name, obj, section, parent):
    if what != "class":
        return None

    if (docstring := obj.__doc__) is None:  # inherited member w/o docstring
        for base_class in parent.__mro__[1:]:
            if base_class in (ABC, object):
                return None
            if (obj := getattr(base_class, name)) is None:
                continue
            if (docstring := obj.__doc__) is not None:
                break

    for line in docstring.splitlines():
        if match := match_category(line):
            return match.group(1)

    return None
