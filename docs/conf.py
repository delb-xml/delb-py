# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config
import sys

# -- Path setup --------------------------------------------------------------

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve() / "sphinx-extensions"))


from importlib import metadata
import re


# -- Project information -----------------------------------------------------

project = "delb"
copyright = "2018-'24, Frank Sachsenheim"
author = "Frank Sachsenheim"

# The full version, including alpha/beta/rc tags
release = metadata.version(project)
# The short X.Y version
version = re.match(r"(^\d+\.\d+).*", release).group(1)


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # in sphinx-extensions
    "class_members_categories",
    "namedtuples",
    # from the cheeseshop
    "autodocsumm",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = {".rst": "restructuredtext"}

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"
pygments_dark_style = "monokai"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

html_theme = "furo"

html_logo = "images/delb_logo.svg"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    "navigation_with_keys": True,
    "source_repository": "https://github.com/delb-xml/delb-py/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = ["styles.css"]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}

html_domain_indices = False


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "delbdoc"


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "delb.tex",
        "delb Documentation",
        "Frank Sachsenheim",
        "manual",
    ),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "delb", "delb Documentation", [author], 1)]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "delb",
        "delb Documentation",
        author,
        "delb",
        "One line description of project.",
        "Miscellaneous",
    ),
]


# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ["search.html"]


# -- Extension configuration -------------------------------------------------

# -- Options for autodoc extension -------------------------------------------

autodoc_default_options = {
    "inherited-members": True,
    "members": True,
}

autodoc_type_aliases = {
    "Filter": "delb.typing.Filter",
    "Loader": "delb.typing.Loader",
    "LoaderConstraint": "delb.typing.LoaderConstraint",
    "LoaderResult": "delb.typing.LoaderResult",
    "NamespaceDeclarations": "delb.typing.NamespaceDeclarations",
    "NodeBase": "delb.NodeBase",
    "NodeSource": "delb.typing.NodeSource",
}

# -- Options for autodocsumm extension ---------------------------------------

MEMBER_SECTIONS_ORDER = (
    "Node properties",
    "content properties",
    "Related",
    "Attributes",
    "query",
    "fetch",
    "iterate",
    "add nodes",
    "remove",
    "Methods",
    "",  # fallback returns lowest weight
)


def autodocsumm_sections_sort(item: str) -> int:
    for weight, substring in enumerate(MEMBER_SECTIONS_ORDER):
        if substring in item:
            return weight


autodocsumm_section_sorter = autodocsumm_sections_sort


# -- Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}


# -- Options for doctest extension -------------------------------------------


doctest_global_setup = """
import types
from typing import Any
from delb import *
"""
