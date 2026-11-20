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
document_issue = "5"
document_date = "2026-11-20"
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

# Panel colours of annunciator. The same values are in
# docs/_static/latex/annunciatorlogo.sty (PDF form and logo).
PANEL = {
    "slate": "#1E2A33",       # panel slate: bezel, titles
    "steel": "#5B6B78",       # steel: secondary text, rules
    "amber": "#F5A800",       # lamp amber: the lit window
    "amber-deep": "#8F5B00",  # amber for text on paper
    "red": "#C8102E",         # alarm red
    "green": "#2E7D4F",       # normal green
    "blue": "#2F6FA3",        # advisory blue
    "lens": "#ECE7DA",        # unlit lens
    "paper": "#FBFAF7",       # paper
}
HEADING_FONTS = (
    '"Roboto Condensed", Bahnschrift, "DIN Alternate", "Arial Narrow", '
    "system-ui, sans-serif"
)


def _admonitions(note, warning, alarm, good, alpha):
    """Return the Furo variables of the admonition colours."""
    groups = {
        note: ("note", "seealso"),
        warning: ("warning", "important", "attention", "admonition-todo"),
        alarm: ("caution", "danger", "error"),
        good: ("tip", "hint"),
    }
    variables = {}
    for colour, kinds in groups.items():
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
        for kind in kinds:
            variables[f"color-admonition-title--{kind}"] = colour
            variables[f"color-admonition-title-background--{kind}"] = (
                f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"
            )
    return variables


html_theme = "furo"
html_title = f"annunciator {release} User Manual ({document_number})"
html_static_path = ["_static/css", "_static/logo"]
html_css_files = ["annunciator.css"]
html_favicon = "_static/logo/favicon.svg"
templates_path = ["_templates"]
html_context = {
    "document_number": document_number,
    "document_issue": document_issue,
}
html_last_updated_fmt = document_date
html_theme_options = {
    "sidebar_hide_name": True,
    "light_css_variables": {
        "font-stack--headings": HEADING_FONTS,
        "color-brand-primary": PANEL["amber-deep"],
        "color-brand-content": PANEL["amber-deep"],
        "color-brand-visited": "#6E4A0C",
        "color-foreground-primary": PANEL["slate"],
        "color-foreground-secondary": "#46535E",
        "color-background-primary": "#FFFFFF",
        "color-background-secondary": PANEL["paper"],
        "color-sidebar-background": "#F4F1EA",
        "color-sidebar-item-background--hover": PANEL["lens"],
        "color-sidebar-link-text": "#2F3D48",
        "color-sidebar-link-text--top-level": PANEL["slate"],
        "color-table-header-background": PANEL["slate"],
        "color-table-border": "#D5CFC0",
        "color-inline-code-background": "#F3F0E8",
        "color-highlighted-background": "#FCEBB8",
        **_admonitions(PANEL["blue"], PANEL["amber"], PANEL["red"],
                       PANEL["green"], 0.12),
        "ann-slate": PANEL["slate"],
        "ann-steel": PANEL["steel"],
        "ann-amber": PANEL["amber"],
        "ann-heading": PANEL["slate"],
        "ann-plate": PANEL["slate"],
        "ann-plate-text": PANEL["lens"],
        "ann-plate-muted": "#AAB4BC",
        "ann-label": PANEL["lens"],
        "ann-label-text": PANEL["slate"],
        "ann-selection": "rgba(245, 168, 0, 0.30)",
        "ann-figure": "transparent",
    },
    "dark_css_variables": {
        "font-stack--headings": HEADING_FONTS,
        "color-brand-primary": PANEL["amber"],
        "color-brand-content": PANEL["amber"],
        "color-brand-visited": "#D9A441",
        "color-foreground-primary": "#E8E6E1",
        "color-foreground-secondary": "#B9C0C6",
        "color-background-primary": "#12171C",
        "color-background-secondary": "#182128",
        "color-sidebar-background": "#182128",
        "color-sidebar-item-background--hover": "#22303A",
        "color-sidebar-link-text": "#C9CED2",
        "color-sidebar-link-text--top-level": "#E8E6E1",
        "color-table-header-background": "#2A3945",
        "color-table-border": "#33434F",
        "color-inline-code-background": "#1F2A33",
        "color-highlighted-background": "rgba(245, 168, 0, 0.25)",
        **_admonitions("#6FA8DC", PANEL["amber"], "#FF6B7A", "#5CC28A", 0.16),
        "ann-slate": "#22303A",
        "ann-steel": "#7B8B98",
        "ann-amber": PANEL["amber"],
        "ann-heading": "#F1EEE6",
        "ann-plate": PANEL["slate"],
        "ann-plate-text": PANEL["lens"],
        "ann-plate-muted": "#AAB4BC",
        "ann-label": "#22303A",
        "ann-label-text": PANEL["lens"],
        "ann-selection": "rgba(245, 168, 0, 0.35)",
        "ann-figure": "#F7F5F0",
    },
}

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
    # Contents and lists in slate text (annunciatortheme.sty).
    "tableofcontents": r"\anncontents",
    # Body text: Latin Modern. Headings: Roboto Condensed (annunciatortheme).
    "fontpkg": r"\usepackage{lmodern}",
    # annunciatortheme.sty makes the chapter headings.
    "fncychap": "",
    "preamble": "\n".join([
        r"\setcounter{tocdepth}{2}",
        rf"\newcommand*\anndocnumber{{{document_number}}}",
        rf"\newcommand*\annissue{{{document_issue}}}",
        rf"\newcommand*\anndate{{{document_date}}}",
        rf"\newcommand*\annversion{{{release}}}",
        r"\newcommand*\annsubtitle{Error, warning and information handling"
        r" and logging with message catalogues}",
        r"\usepackage{annunciatortheme}",
    ]),
}
latex_additional_files = [
    "_static/latex/annunciatorlogo.sty",
    "_static/latex/annunciatortheme.sty",
]
latex_show_urls = "footnote"
