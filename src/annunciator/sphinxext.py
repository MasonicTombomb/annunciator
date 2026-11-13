"""Sphinx extension for message catalogues.

The extension adds the directive ``annunciator-catalogue`` and the role
``msg``. The directive writes the reference text for all messages of a
catalogue. Thus the documentation and the software always agree.

To use the extension, add ``"annunciator.sphinxext"`` to the list
``extensions`` in the file ``conf.py``. Then write, for example:

.. code-block:: rst

   .. annunciator-catalogue:: APP
      :module: myapp.messages
      :min-severity: WARNING

   Refer to :msg:`APP-E-0001`.

The directive has these options:

``module``
    A module to import before the directive reads the catalogue. Use
    this option for the module that defines your catalogue.
``min-severity``
    Write only the messages of this severity or higher.
``category``
    Write only the messages in this category.
``heading``
    The character for the section underline. The default is ``~``.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, List

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList

from ._version import __version__
from .catalogue import get_catalogue, lookup

__all__ = ["CatalogueDirective", "msg_role", "setup", "target_name"]


def target_name(code: str) -> str:
    """Return the reference label for a message code."""
    return "msg-" + code.lower()


def _escape(text: str) -> str:
    """Protect characters that have a function in reStructuredText."""
    for char in ("\\", "*", "`", "|"):
        text = text.replace(char, "\\" + char)
    return text


class CatalogueDirective(Directive):
    """Directive that writes the messages of one catalogue."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec = {
        "module": directives.unchanged,
        "min-severity": directives.unchanged,
        "category": directives.unchanged,
        "heading": directives.single_char_or_unicode,
    }

    def run(self) -> List[nodes.Node]:
        from sphinx.util.nodes import nested_parse_with_titles

        module = self.options.get("module")
        if module:
            importlib.import_module(module)
        catalogue = get_catalogue(self.arguments[0].strip())
        items = catalogue.select(
            minimum=self.options.get("min-severity"),
            category=self.options.get("category"),
        )
        mark = self.options.get("heading", "~")
        lines: List[str] = []
        for item in items:
            lines += [
                f".. _{target_name(item.code)}:",
                "",
                item.code,
                mark * len(item.code),
                "",
                f".. index:: single: {item.code}",
                "",
                f":Severity: {item.severity.name}",
                f":Message: ``{item.text}``",
            ]
            if item.category:
                lines.append(f":Category: {_escape(item.category)}")
            if item.cause:
                lines.append(f":Cause: {_escape(item.cause)}")
            if item.remedy:
                lines.append(f":Remedy: {_escape(item.remedy)}")
            if item.since:
                lines.append(f":Since: {_escape(item.since)}")
            lines.append("")
        container = nodes.section()
        container.document = self.state.document
        source = f"<annunciator-catalogue {catalogue.prefix}>"
        nested_parse_with_titles(
            self.state, StringList(lines, source=source), container
        )
        return container.children


def msg_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """Role that makes a reference to the section of a message code."""
    from sphinx import addnodes

    code = text.strip()
    literal = nodes.literal(code, code)
    if lookup(code) is None:
        message = inliner.reporter.warning(
            f"message code {code!r} is not in a registered catalogue", line=lineno
        )
        return [literal], [message]
    reference = addnodes.pending_xref(
        "",
        refdomain="std",
        reftype="ref",
        reftarget=target_name(code),
        refexplicit=True,
        refwarn=True,
    )
    reference += literal
    return [reference], []


def setup(app: Any) -> Dict[str, Any]:
    """Register the directive and the role with Sphinx."""
    app.add_directive("annunciator-catalogue", CatalogueDirective)
    app.add_role("msg", msg_role)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
