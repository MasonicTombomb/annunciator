"""Static check of message codes in source code.

The check reads Python source files without running them. It compares
the message codes in the files with the registered catalogues. It finds
three types of problem:

``undefined``
    The source code uses a code that has no definition. At run time,
    the message has no text, no cause and no remedy.
``missing-field``
    A call gives a code but does not give a value for a replacement
    field of the message text.
``unused``
    A catalogue defines a code that the source code does not use.

Import the modules that define your catalogues before you call
:func:`lint_paths`. The command ``annunciator lint`` does this with the
option ``--import``.

Examples
--------
>>> import os, tempfile
>>> from annunciator.lint import lint_paths
>>> folder = tempfile.mkdtemp()
>>> with open(os.path.join(folder, "demo.py"), "w") as stream:
...     _ = stream.write('log.event("ANN-E-9999")\\nlog.event("ANN-E-0001")\\n')
>>> [(f.kind, f.code, f.line) for f in lint_paths([folder], unused=False)]
[('undefined', 'ANN-E-9999', 1), ('missing-field', 'ANN-E-0001', 2)]
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Union

from .catalogue import CODE_PATTERN, catalogues, lookup

__all__ = ["LintFinding", "lint_paths"]

#: Keyword arguments that are not replacement fields.
_RESERVED = {
    "code", "strict", "exc_info", "stack_info", "stacklevel", "context",
    "cause", "remedy", "category", "severity", "logger", "key", "operation",
}


@dataclass(frozen=True)
class LintFinding:
    """One finding of the static check.

    Attributes
    ----------
    path : str
        The path of the source file, or the empty text for ``unused``.
    line : int
        The line number, or 0 for ``unused``.
    kind : str
        ``"undefined"``, ``"missing-field"``, ``"unused"`` or
        ``"syntax"``.
    code : str
        The message code.
    detail : str
        More data about the finding.
    """

    path: str
    line: int
    kind: str
    code: str
    detail: str = ""

    @property
    def is_error(self) -> bool:
        """``True`` for all kinds but ``unused``."""
        return self.kind != "unused"

    def to_text(self) -> str:
        """Return the finding as one line of text."""
        where = f"{self.path}:{self.line}: " if self.path else ""
        tail = f" ({self.detail})" if self.detail else ""
        return f"{where}{self.kind}: {self.code}{tail}"


def _literal_code(node: Optional[ast.AST]) -> Optional[str]:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and CODE_PATTERN.match(node.value)
    ):
        return node.value
    return None


def _python_files(paths: Iterable[Union[str, Path]]) -> List[Path]:
    files: List[Path] = []
    for item in paths:
        base = Path(item)
        if base.is_dir():
            files.extend(sorted(base.rglob("*.py")))
        else:
            files.append(base)
    return files


def lint_paths(
    paths: Iterable[Union[str, Path]],
    *,
    prefixes: Optional[Sequence[str]] = None,
    unused: bool = True,
) -> List[LintFinding]:
    """Examine the message codes in Python source files.

    Parameters
    ----------
    paths
        Python files or directories. The function reads all ``.py``
        files in a directory and in its subdirectories.
    prefixes
        The catalogue prefixes to examine. The default is all
        registered catalogues. The check for ``unused`` codes does not
        include the catalogue ``ANN`` unless you give it here.
    unused
        If ``True``, also find the codes that the source does not use.

    Returns
    -------
    list of LintFinding
        The findings, in the sequence of the files and the lines.

    Notes
    -----
    The check finds only codes that are complete text in the source
    code. It cannot find a code that the program makes at run time.
    """
    registered = {item.prefix for item in catalogues()}
    wanted: Set[str] = set(prefixes) if prefixes else set(registered)
    findings: List[LintFinding] = []
    used: Dict[str, int] = {}

    for file in _python_files(paths):
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            findings.append(LintFinding(str(file), 0, "syntax", "-", str(exc)))
            continue
        reported: Set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                code = None
                target: Optional[ast.AST] = None
                is_event = (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "event"
                )
                if is_event and node.args:
                    target = node.args[0]
                    code = _literal_code(target)
                for keyword in node.keywords:
                    if keyword.arg == "code" and _literal_code(keyword.value):
                        target = keyword.value
                        code = _literal_code(keyword.value)
                definition = lookup(code) if code else None
                if definition is None or code.split("-")[0] not in wanted:
                    continue
                if any(keyword.arg is None for keyword in node.keywords):
                    continue  # ``**fields``: the values are not known
                given = {keyword.arg for keyword in node.keywords} - _RESERVED
                missing = [
                    name for name in definition.field_names if name not in given
                ]
                # A message text that the call gives replaces the fields.
                has_message = bool(node.args) and not is_event
                if missing and not has_message:
                    findings.append(
                        LintFinding(
                            str(file), node.lineno, "missing-field", code,
                            "no value for: " + ", ".join(missing),
                        )
                    )
            code = _literal_code(node)
            if code is None:
                continue
            used[code] = used.get(code, 0) + 1
            prefix = code.split("-")[0]
            if prefix in wanted and lookup(code) is None:
                line = getattr(node, "lineno", 0)
                if line not in reported:
                    reported.add(line)
                    findings.append(
                        LintFinding(str(file), line, "undefined", code)
                    )

    findings.sort(key=lambda item: (item.path, item.line, item.kind))
    if unused:
        for catalogue in catalogues():
            if catalogue.prefix not in wanted:
                continue
            if catalogue.prefix == "ANN" and not (prefixes and "ANN" in prefixes):
                continue
            for definition in catalogue:
                if definition.code not in used:
                    findings.append(
                        LintFinding("", 0, "unused", definition.code, definition.text)
                    )
    return findings
