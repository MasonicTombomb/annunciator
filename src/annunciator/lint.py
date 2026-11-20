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
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple, Type,
    Union,
)

from ._coded import CodedMixin
from .catalogue import CODE_PATTERN, catalogues, lookup

__all__ = ["LintFinding", "lint_paths"]

#: Parameters of ``StructuredLogger.event``. ``event`` gives all other
#: keyword arguments to the message text (``**fields``), also names such as
#: ``operation``, ``category`` or ``key``.
_EVENT_PARAMETERS = frozenset({"code", "strict", "exc_info", "stacklevel"})

#: Parameters of :func:`annunciator.warn`.
_WARN_PARAMETERS = frozenset(
    {"message", "category", "code", "stacklevel", "context"}
)

#: Keyword arguments that are not replacement fields in a call to a
#: function that the check does not know. This is the union of the
#: parameters of the functions that take a ``code=`` keyword: the log
#: methods (``log``, ``info``, ..., ``once``, ``every``, ``throttle``),
#: ``warn``, the coded errors and warnings and the soft checks.
_RESERVED = frozenset({
    "code", "strict", "exc_info", "stack_info", "stacklevel", "context",
    "cause", "remedy", "category", "severity", "logger", "key", "message",
    "on_fail", "error",
})


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


def _is_none(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _gives_message(node: ast.Call) -> bool:
    """Return ``True`` if a call gives its own message text.

    A message text replaces the text of the definition. Thus the
    replacement fields are not necessary. ``None`` (for example
    ``warn(None, DataQualityWarning, code=...)``) is not a message text.
    """
    if node.args and not _is_none(node.args[0]):
        return True
    return any(
        keyword.arg == "message" and not _is_none(keyword.value)
        for keyword in node.keywords
    )


def _callee_name(node: ast.Call) -> Optional[str]:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _init_parameters(cls: type) -> Set[str]:
    """Return the named parameters of ``__init__`` in the coded part of the MRO."""
    names: Set[str] = set()
    for klass in cls.__mro__:
        if not (isinstance(klass, type) and issubclass(klass, CodedMixin)):
            continue
        init = vars(klass).get("__init__")
        if not callable(init):
            continue
        try:
            signature = inspect.signature(init)
        except (TypeError, ValueError):
            continue
        names.update(
            name
            for name, parameter in signature.parameters.items()
            if name != "self"
            and parameter.kind
            not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
        )
    return names


def _coded_classes() -> Dict[str, Tuple[FrozenSet[str], FrozenSet[str]]]:
    """Map the names of the loaded coded errors and warnings to their data.

    The data is the set of parameters that are not replacement fields,
    and the set of fields that the class supplies itself. If two classes
    have the same name, the function joins their sets. Thus the check
    does not report a field that one of the classes accepts.
    """
    from .errors import AggregateError

    found: Dict[str, Tuple[Set[str], Set[str]]] = {}
    pending: List[Type[CodedMixin]] = [CodedMixin]
    seen: Set[Type[CodedMixin]] = set()
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
        if cls is CodedMixin:
            continue  # the base class is not called with a code
        parameters, implied = found.setdefault(cls.__name__, (set(), set()))
        parameters.update(_init_parameters(cls) | {"code"})
        if issubclass(cls, AggregateError):
            implied.add("count")  # set from the length of ``errors``
    return {
        name: (frozenset(parameters), frozenset(implied))
        for name, (parameters, implied) in found.items()
    }


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
    coded = _coded_classes()

    for file in _python_files(paths):
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            findings.append(LintFinding(str(file), 0, "syntax", "-", str(exc)))
            continue
        reported: Set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_code: Optional[str] = None
                is_event = (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "event"
                )
                if is_event and node.args:
                    call_code = _literal_code(node.args[0])
                for keyword in node.keywords:
                    if keyword.arg == "code" and _literal_code(keyword.value):
                        call_code = _literal_code(keyword.value)
                if not call_code or call_code.split("-")[0] not in wanted:
                    continue
                definition = lookup(call_code)
                if definition is None:
                    continue
                if any(keyword.arg is None for keyword in node.keywords):
                    continue  # ``**fields``: the values are not known
                # Only the parameters of the called function are not
                # replacement fields. A name that is a parameter of one
                # function can be a field of another (``event`` gives
                # ``operation``, ``key`` or ``category`` to the text).
                callee = _callee_name(node)
                implied: FrozenSet[str] = frozenset()
                if is_event:
                    reserved = _EVENT_PARAMETERS
                elif callee == "warn":
                    reserved = _WARN_PARAMETERS
                elif callee is not None and callee in coded:
                    reserved, implied = coded[callee]
                else:
                    reserved = _RESERVED
                given = {keyword.arg for keyword in node.keywords} - reserved
                given |= implied
                missing = [
                    name for name in definition.field_names if name not in given
                ]
                # A message text that the call gives replaces the fields.
                has_message = not is_event and _gives_message(node)
                if missing and not has_message:
                    findings.append(
                        LintFinding(
                            str(file), node.lineno, "missing-field", call_code,
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
