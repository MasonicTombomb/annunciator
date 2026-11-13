"""Sphinx configuration for the annunciator user manual (ANN-UM-001)."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

from annunciator import __version__  # noqa: E402

# -- Document identification (ISO/IEC/IEEE 26514: identification data) ------

project = "annunciator"
author = "Tom Scott"
copyright = "2026, Tom Scott"
version = __version__
release = __version__
document_number = "ANN-UM-001"
document_issue = "3"
document_date = "2026-11-13"
today = document_date

# -- General ----------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "annunciator.sphinxext",
]
language = "en"
exclude_patterns = ["_build"]
numfig = True
numfig_format = {
    "figure": "Figure %s",
    "table": "Table %s",
    "code-block": "Example %s",
    "section": "Section %s",
}
rst_prolog = f"""
.. |docnum| replace:: {document_number}
.. |issue| replace:: {document_issue}
.. |date| replace:: {document_date}
"""

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {"members": True, "show-inheritance": True}
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_rtype = False

# -- HTML (on-screen form: navigation, index and search) ---------------------

html_theme = "furo"
html_title = f"annunciator {release} User Manual ({document_number})"
html_static_path = ["_static"]
html_last_updated_fmt = document_date

# -- PDF (print form) --------------------------------------------------------

latex_engine = "pdflatex"
latex_documents = [
    (
        "index",
        f"{document_number}.tex",
        "annunciator User Manual",
        author,
        "manual",
    )
]
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "10pt",
    "releasename": f"{document_number}, Issue {document_issue}, software version",
    "tableofcontents": (
        r"\sphinxtableofcontents\listoffigures\listoftables"
    ),
    # Fonts that are in a basic LaTeX installation.
    "fontpkg": r"\usepackage{lmodern}",
    "preamble": r"\setcounter{tocdepth}{2}",
}
latex_show_urls = "footnote"
