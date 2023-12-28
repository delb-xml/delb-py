def setup(app):
    app.connect("autodoc-process-docstring", namedtuple_strip_alias_reference)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def namedtuple_strip_alias_reference(app, what, name, obj, options, lines):
    if lines and lines[0].startswith("Alias for field number "):
        lines.clear()
