"""Message catalogues.

A message catalogue is a set of message definitions. Each definition has
a unique message code, a text template, a probable cause and a remedy.

A message code has three parts::

    APP-E-0042
    |   |  |
    |   |  +-- message number (four digits)
    |   +----- severity letter (T, D, I, N, W, E or C)
    +--------- catalogue prefix (two to eight characters)

When you use message codes, each message has one definition. The log
records, the exceptions and the user documentation then agree.

Examples
--------
>>> from annunciator import MessageCatalogue, Severity
>>> cat = MessageCatalogue("DEMO", "Demonstration messages", replace=True)
>>> definition = cat.define(
...     1, Severity.ERROR, "The file '{path}' is not available.",
...     cause="The file does not exist.",
...     remedy="Make sure that the path is correct.",
... )
>>> definition.code
'DEMO-E-0001'
>>> definition.format(path="a.csv")
"The file 'a.csv' is not available."
"""

from __future__ import annotations

import json
import re
import string
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, Union

from .levels import Severity, SeverityLike

__all__ = [
    "CODE_PATTERN",
    "MessageDefinition",
    "MessageCatalogue",
    "parse_code",
    "make_code",
    "register_catalogue",
    "unregister_catalogue",
    "get_catalogue",
    "catalogues",
    "lookup",
    "explain",
    "BUILTIN",
]

#: Regular expression that a message code must agree with.
CODE_PATTERN = re.compile(
    r"^(?P<prefix>[A-Z][A-Z0-9]{1,7})-(?P<letter>[TDINWEC])-(?P<number>\d{4})$"
)
_PREFIX_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")


class _SafeDict(dict):
    """Dictionary that keeps a placeholder when a field is not available."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _catalogue_error(code: str, **fields: Any) -> Exception:
    """Make a :class:`~annunciator.errors.CatalogueError` (late import)."""
    from .errors import CatalogueError

    return CatalogueError(code=code, **fields)


def parse_code(code: str) -> Tuple[str, Severity, int]:
    """Divide a message code into its parts.

    Parameters
    ----------
    code
        The message code, for example ``APP-E-0042``.

    Returns
    -------
    tuple
        The prefix, the severity and the message number.

    Raises
    ------
    CatalogueError
        If the format of the code is not correct (``ANN-E-0101``).
    """
    match = CODE_PATTERN.match(code) if isinstance(code, str) else None
    if match is None:
        raise _catalogue_error("ANN-E-0101", item=code)
    return (
        match.group("prefix"),
        Severity.from_letter(match.group("letter")),
        int(match.group("number")),
    )


def make_code(prefix: str, severity: SeverityLike, number: int) -> str:
    """Make a message code from its parts.

    Parameters
    ----------
    prefix
        The catalogue prefix.
    severity
        The severity of the message.
    number
        The message number, from 0 to 9999.

    Returns
    -------
    str
        The message code.

    Raises
    ------
    CatalogueError
        If a part is not correct (``ANN-E-0101``).
    """
    try:
        code = f"{prefix}-{Severity.coerce(severity).letter}-{int(number):04d}"
    except (TypeError, ValueError):
        code = f"{prefix}-{severity}-{number}"
    parse_code(code)
    return code


@dataclass(frozen=True)
class MessageDefinition:
    """Definition of one message.

    Parameters
    ----------
    code
        The unique message code.
    text
        The message text. The text can contain replacement fields in the
        :meth:`str.format` syntax, for example ``{path}``.
    cause
        The probable cause of the event.
    remedy
        The action that the user must do to correct the condition.
    category
        An optional group name, for example ``Configuration``.
    since
        The version of your software that added the message.
    """

    code: str
    text: str
    cause: str = ""
    remedy: str = ""
    category: str = ""
    since: str = ""

    def __post_init__(self) -> None:
        parse_code(self.code)
        if not isinstance(self.text, str) or not self.text.strip():
            raise _catalogue_error("ANN-E-0101", item=self.code)

    @property
    def prefix(self) -> str:
        """The catalogue prefix of the code."""
        return parse_code(self.code)[0]

    @property
    def severity(self) -> Severity:
        """The severity that the code letter identifies."""
        return parse_code(self.code)[1]

    @property
    def number(self) -> int:
        """The message number of the code."""
        return parse_code(self.code)[2]

    @property
    def field_names(self) -> Tuple[str, ...]:
        """The names of the replacement fields in the text."""
        names: List[str] = []
        for _, name, _, _ in string.Formatter().parse(self.text):
            if name:
                root = re.split(r"[.\[]", name, maxsplit=1)[0]
                if root and root not in names:
                    names.append(root)
        return tuple(names)

    def format(self, **fields: Any) -> str:
        """Return the message text with the field values.

        If a field value is not available, the placeholder stays in the
        text. The method does not raise an exception.

        Parameters
        ----------
        **fields
            The values for the replacement fields.
        """
        try:
            return self.text.format_map(_SafeDict(fields))
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            return self.text

    def to_dict(self) -> Dict[str, str]:
        """Return the definition as a dictionary without empty items."""
        data = {
            "code": self.code,
            "text": self.text,
            "cause": self.cause,
            "remedy": self.remedy,
            "category": self.category,
            "since": self.since,
        }
        return {key: value for key, value in data.items() if value}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MessageDefinition":
        """Make a definition from a dictionary.

        Raises
        ------
        CatalogueError
            If the dictionary does not contain a correct code and text.
        """
        try:
            return cls(
                code=str(data["code"]),
                text=str(data["text"]),
                cause=str(data.get("cause", "")),
                remedy=str(data.get("remedy", "")),
                category=str(data.get("category", "")),
                since=str(data.get("since", "")),
            )
        except KeyError as exc:
            raise _catalogue_error("ANN-E-0101", item=str(data.get("code", "?"))
            ) from exc


class MessageCatalogue:
    """A set of message definitions that have the same prefix.

    Parameters
    ----------
    prefix
        The catalogue prefix. The prefix has two to eight characters. It
        starts with a capital letter. The other characters are capital
        letters or digits.
    title
        A short title for the documentation.
    register
        If ``True``, add the catalogue to the registry of the library.
        Then :func:`lookup` can find its messages.
    replace
        If ``True``, replace a registered catalogue that has the same
        prefix. Use this option in an interactive session.

    Raises
    ------
    CatalogueError
        If the prefix is not correct (``ANN-E-0101``) or is already
        registered (``ANN-E-0105``).
    """

    def __init__(
        self,
        prefix: str,
        title: str = "",
        *,
        register: bool = True,
        replace: bool = False,
    ) -> None:
        if not isinstance(prefix, str) or not _PREFIX_PATTERN.match(prefix):
            raise _catalogue_error("ANN-E-0101", item=str(prefix))
        self.prefix = prefix
        self.title = title or f"{prefix} messages"
        self._messages: Dict[str, MessageDefinition] = {}
        self._lock = threading.RLock()
        if register:
            register_catalogue(self, replace=replace)

    def __repr__(self) -> str:
        return f"MessageCatalogue({self.prefix!r}, messages={len(self)})"

    def __len__(self) -> int:
        return len(self._messages)

    def __iter__(self) -> Iterator[MessageDefinition]:
        with self._lock:
            ordered = sorted(self._messages.values(), key=lambda d: d.number)
        return iter(ordered)

    def __contains__(self, code: object) -> bool:
        return code in self._messages

    def __getitem__(self, code: str) -> MessageDefinition:
        return self.get(code)

    def add(self, definition: MessageDefinition) -> MessageDefinition:
        """Add a definition to the catalogue.

        Raises
        ------
        CatalogueError
            If the prefix of the code is not the catalogue prefix
            (``ANN-E-0101``). Also if the code or the message number is
            already in the catalogue (``ANN-E-0102``).
        """
        if definition.prefix != self.prefix:
            raise _catalogue_error("ANN-E-0101", item=definition.code)
        with self._lock:
            numbers = {item.number for item in self._messages.values()}
            if definition.code in self._messages or definition.number in numbers:
                raise _catalogue_error("ANN-E-0102", item=definition.code)
            self._messages[definition.code] = definition
        return definition

    def define(
        self,
        number: int,
        severity: SeverityLike,
        text: str,
        *,
        cause: str = "",
        remedy: str = "",
        category: str = "",
        since: str = "",
    ) -> MessageDefinition:
        """Make a definition and add it to the catalogue.

        Parameters
        ----------
        number
            The message number, from 0 to 9999. A number can occur only
            one time in a catalogue.
        severity
            The severity of the message.
        text
            The message text with optional replacement fields.
        cause
            The probable cause.
        remedy
            The corrective action.
        category
            An optional group name.
        since
            The version of your software that added the message.

        Returns
        -------
        MessageDefinition
            The new definition.
        """
        definition = MessageDefinition(
            code=make_code(self.prefix, severity, number),
            text=text,
            cause=cause,
            remedy=remedy,
            category=category,
            since=since,
        )
        return self.add(definition)

    def find(self, code: str) -> Optional[MessageDefinition]:
        """Return the definition for a code, or ``None``."""
        return self._messages.get(code)

    def get(self, code: str) -> MessageDefinition:
        """Return the definition for a code.

        Raises
        ------
        CatalogueError
            If the code is not in the catalogue (``ANN-E-0103``).
        """
        definition = self._messages.get(code)
        if definition is None:
            raise _catalogue_error("ANN-E-0103", item=code)
        return definition

    def select(
        self,
        *,
        severity: Optional[SeverityLike] = None,
        minimum: Optional[SeverityLike] = None,
        category: Optional[str] = None,
        text: Optional[str] = None,
    ) -> List[MessageDefinition]:
        """Return the definitions that agree with all given conditions.

        Parameters
        ----------
        severity
            Keep only the messages that have this severity.
        minimum
            Keep only the messages that have this severity or higher.
        category
            Keep only the messages in this category.
        text
            Keep only the messages that contain this text in the code,
            the text, the cause or the remedy. Letter case is not
            important.
        """
        result = []
        needle = text.lower() if text else None
        for item in self:
            if severity is not None and item.severity != Severity.coerce(severity):
                continue
            if minimum is not None and item.severity < Severity.coerce(minimum):
                continue
            if category is not None and item.category != category:
                continue
            if needle is not None:
                haystack = " ".join(
                    (item.code, item.text, item.cause, item.remedy)
                ).lower()
                if needle not in haystack:
                    continue
            result.append(item)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Return the catalogue as a dictionary that JSON can contain."""
        return {
            "prefix": self.prefix,
            "title": self.title,
            "messages": [item.to_dict() for item in self],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        register: bool = True,
        replace: bool = False,
    ) -> "MessageCatalogue":
        """Make a catalogue from a dictionary.

        The dictionary must have the structure that :meth:`to_dict`
        returns.
        """
        try:
            prefix = str(data["prefix"])
            messages = list(data.get("messages", []))
        except (KeyError, TypeError) as exc:
            raise _catalogue_error("ANN-E-0101", item="?") from exc
        catalogue = cls(
            prefix, str(data.get("title", "")), register=False
        )
        for item in messages:
            catalogue.add(MessageDefinition.from_dict(item))
        if register:
            register_catalogue(catalogue, replace=replace)
        return catalogue

    @classmethod
    def load(
        cls,
        path: Union[str, Path],
        *,
        register: bool = True,
        replace: bool = False,
    ) -> "MessageCatalogue":
        """Read a catalogue from a JSON file or a TOML file.

        Parameters
        ----------
        path
            The path of the file. The suffix must be ``.json`` or
            ``.toml``.
        register
            If ``True``, add the catalogue to the registry.
        replace
            If ``True``, replace a registered catalogue that has the
            same prefix.

        Raises
        ------
        CatalogueError
            If the library cannot read the file (``ANN-E-0104``).
        """
        file = Path(path)
        try:
            if file.suffix.lower() == ".toml":
                data = _load_toml(file)
            else:
                data = json.loads(file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - convert to one error type
            raise _catalogue_error(
                "ANN-E-0104", path=str(file), reason=str(exc)
            ) from exc
        return cls.from_dict(data, register=register, replace=replace)

    def save(self, path: Union[str, Path]) -> Path:
        """Write the catalogue to a JSON file.

        Returns
        -------
        pathlib.Path
            The path of the file.
        """
        file = Path(path)
        file.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return file


def _load_toml(path: Path) -> Dict[str, Any]:
    """Read a TOML file. Python 3.11 or the ``tomli`` package is necessary."""
    try:
        import tomllib as toml_reader
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        import tomli as toml_reader  # type: ignore[no-redef]
    with path.open("rb") as stream:
        return toml_reader.load(stream)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

_REGISTRY: Dict[str, MessageCatalogue] = {}
_REGISTRY_LOCK = threading.RLock()


def register_catalogue(
    catalogue: MessageCatalogue, *, replace: bool = False
) -> MessageCatalogue:
    """Add a catalogue to the registry of the library.

    Parameters
    ----------
    catalogue
        The catalogue to add.
    replace
        If ``True``, replace a catalogue that has the same prefix.

    Raises
    ------
    CatalogueError
        If the prefix is already registered and ``replace`` is ``False``
        (``ANN-E-0105``).
    """
    with _REGISTRY_LOCK:
        current = _REGISTRY.get(catalogue.prefix)
        if current is not None and current is not catalogue and not replace:
            raise _catalogue_error("ANN-E-0105", prefix=catalogue.prefix)
        _REGISTRY[catalogue.prefix] = catalogue
    return catalogue


def unregister_catalogue(prefix: str) -> Optional[MessageCatalogue]:
    """Remove a catalogue from the registry.

    Returns
    -------
    MessageCatalogue or None
        The catalogue that the function removed.
    """
    with _REGISTRY_LOCK:
        return _REGISTRY.pop(prefix, None)


def get_catalogue(prefix: str) -> MessageCatalogue:
    """Return the registered catalogue that has the given prefix.

    Raises
    ------
    CatalogueError
        If the prefix is not registered (``ANN-E-0103``).
    """
    with _REGISTRY_LOCK:
        catalogue = _REGISTRY.get(prefix)
    if catalogue is None:
        raise _catalogue_error("ANN-E-0103", item=prefix)
    return catalogue


def catalogues() -> List[MessageCatalogue]:
    """Return all registered catalogues in the sequence of their prefixes."""
    with _REGISTRY_LOCK:
        return [_REGISTRY[key] for key in sorted(_REGISTRY)]


def lookup(code: Optional[str]) -> Optional[MessageDefinition]:
    """Find a message definition in all registered catalogues.

    Parameters
    ----------
    code
        The message code.

    Returns
    -------
    MessageDefinition or None
        The definition, or ``None`` if no registered catalogue contains
        the code.
    """
    if not isinstance(code, str):
        return None
    match = CODE_PATTERN.match(code)
    if match is None:
        return None
    with _REGISTRY_LOCK:
        catalogue = _REGISTRY.get(match.group("prefix"))
    return catalogue.find(code) if catalogue is not None else None


def explain(code: str) -> str:
    """Return a text that gives the full definition of a message.

    Parameters
    ----------
    code
        The message code.

    Raises
    ------
    CatalogueError
        If the code is not in a registered catalogue (``ANN-E-0103``).
    """
    definition = lookup(code)
    if definition is None:
        raise _catalogue_error("ANN-E-0103", item=code)
    lines = [
        f"Code:     {definition.code}",
        f"Severity: {definition.severity.name}",
        f"Message:  {definition.text}",
    ]
    if definition.category:
        lines.append(f"Category: {definition.category}")
    if definition.cause:
        lines.append(f"Cause:    {definition.cause}")
    if definition.remedy:
        lines.append(f"Remedy:   {definition.remedy}")
    if definition.since:
        lines.append(f"Since:    {definition.since}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Built-in catalogue
# --------------------------------------------------------------------------

#: The catalogue of the messages that the library itself can give.
BUILTIN = MessageCatalogue("ANN", "Messages of the annunciator library")

_CFG = "Configuration"
_CAT = "Message catalogue"
_HOOK = "Exception hooks"
_HANDLE = "Error handling"
_REPORT = "Reports"

BUILTIN.define(
    1, "E", "The configuration option '{option}' is not known.",
    cause="The configuration contains an option that the library does not "
          "define.",
    remedy="Remove the option or correct its name. Refer to the "
           "configuration reference.",
    category=_CFG, since="1.0.0",
)
BUILTIN.define(
    2, "E", "The value {value!r} is not permitted for the configuration "
            "option '{option}'.",
    cause="The value has an incorrect type or is out of the permitted range.",
    remedy="Set the option to a permitted value. Refer to the configuration "
           "reference.",
    category=_CFG, since="1.0.0",
)
BUILTIN.define(
    3, "E", "The configuration file '{path}' cannot be read: {reason}",
    cause="The file does not exist, you do not have access, or the contents "
          "are not correct.",
    remedy="Make sure that the path is correct and that the file contains "
           "correct TOML or JSON data.",
    category=_CFG, since="1.0.0",
)
BUILTIN.define(
    4, "E", "The configuration file type '{suffix}' is not supported.",
    cause="The suffix of the file name is not .toml or .json.",
    remedy="Use a TOML file or a JSON file.",
    category=_CFG, since="1.0.0",
)
BUILTIN.define(
    10, "D", "Logging is configured. Level: {level}. Handlers: {handlers}.",
    cause="The program called the configure function.",
    remedy="No action is necessary.",
    category=_CFG, since="1.0.0",
)
BUILTIN.define(
    101, "E", "The message code or prefix '{item}' is not correct.",
    cause="The code does not have the format PREFIX-L-NNNN, the prefix is "
          "not correct, or the message text is empty.",
    remedy="Use a prefix of two to eight capital letters or digits, one "
           "severity letter (T, D, I, N, W, E or C) and four digits.",
    category=_CAT, since="1.0.0",
)
BUILTIN.define(
    102, "E", "The message code '{item}' is already in the catalogue.",
    cause="Two definitions in one catalogue have the same code or the same "
          "message number.",
    remedy="Give a different message number to the new definition.",
    category=_CAT, since="1.0.0",
)
BUILTIN.define(
    103, "E", "The message code or prefix '{item}' is not in a registered "
              "catalogue.",
    cause="The code contains a typing error, or the program did not import "
          "the module that defines the catalogue.",
    remedy="Correct the code, or import the module that defines the "
           "catalogue before you use the code.",
    category=_CAT, since="1.0.0",
)
BUILTIN.define(
    104, "E", "The catalogue file '{path}' cannot be read: {reason}",
    cause="The file does not exist, you do not have access, or the contents "
          "are not correct.",
    remedy="Make sure that the path is correct and that the file has the "
           "catalogue file structure.",
    category=_CAT, since="1.0.0",
)
BUILTIN.define(
    105, "E", "The catalogue prefix '{prefix}' is already registered.",
    cause="Two catalogues have the same prefix, or the program made the "
          "same catalogue two times.",
    remedy="Use a different prefix. In an interactive session, set the "
           "parameter replace to True.",
    category=_CAT, since="1.0.0",
)
BUILTIN.define(
    201, "C", "An exception was not caught: {exc_type}: {exc_message}",
    cause="The program raised an exception and no code caught it. The "
          "program stops.",
    remedy="Read the traceback in the log. Correct the cause, or add error "
           "handling to the program.",
    category=_HOOK, since="1.0.0",
)
BUILTIN.define(
    202, "C", "An exception was not caught in the thread '{thread}': "
              "{exc_type}: {exc_message}",
    cause="A thread raised an exception and no code caught it. The thread "
          "stops.",
    remedy="Read the traceback in the log. Add error handling to the "
           "function that the thread runs.",
    category=_HOOK, since="1.0.0",
)
BUILTIN.define(
    203, "E", "The asyncio event loop reported an error: {detail}",
    cause="A task or a callback raised an exception and no code caught it.",
    remedy="Read the traceback in the log. Await the task and catch its "
           "exceptions.",
    category=_HOOK, since="1.0.0",
)
BUILTIN.define(
    204, "E", "Python ignored an exception: {exc_type}: {exc_message} "
              "({detail})",
    cause="An exception occurred where Python cannot raise it, for example "
          "in a __del__ method.",
    remedy="Read the traceback in the log. Correct the code of the object "
           "that the message identifies.",
    category=_HOOK, since="1.0.0",
)
BUILTIN.define(
    205, "W", "{category}: {text}",
    cause="A module issued a Python warning that does not have a message "
          "code.",
    remedy="Read the warning text. Refer to the documentation of the module "
           "that issued the warning.",
    category=_HOOK, since="1.0.0",
)
BUILTIN.define(
    301, "W", "Attempt {attempt} of {attempts} of '{operation}' failed: "
              "{reason}. The next attempt starts in {delay} s.",
    cause="The operation raised an exception that the retry policy accepts.",
    remedy="No action is necessary if a subsequent attempt is successful.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    302, "E", "The operation '{operation}' failed after {attempts} "
              "attempts: {reason}.",
    cause="All attempts of the operation raised an exception.",
    remedy="Read the last exception in the log. Correct its cause and start "
           "the operation again.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    303, "E", "The operation '{operation}' failed: {exc_type}: "
              "{exc_message}",
    cause="The operation raised an exception that does not have a message "
          "code.",
    remedy="Read the traceback in the log and correct the cause.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    304, "E", "{count} errors occurred in '{operation}'.",
    cause="An error collector recorded one or more errors.",
    remedy="Read each error in the log and correct its cause.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    305, "W", "The operation '{operation}' was slow. Time: {elapsed} s. "
              "Limit: {limit} s.",
    cause="The operation used more time than the limit that the program "
          "set.",
    remedy="Examine the load on the computer and the size of the input "
           "data.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    306, "D", "The call of '{function}' started.",
    cause="A function that has the log_calls decorator started.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    307, "D", "The call of '{function}' completed in {elapsed} s.",
    cause="A function that has the log_calls decorator returned.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    308, "I", "The operation '{operation}' completed in {elapsed} s.",
    cause="A timed block completed.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    309, "W", "'{name}' is deprecated since version {since}. {advice}",
    cause="The program uses a function or a class that a future version "
          "will remove.",
    remedy="Change the program as the message tells you.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    310, "E", "The operation '{operation}' did not complete in {limit} s.",
    cause="The operation used more time than the permitted limit.",
    remedy="Increase the limit, or examine why the operation is slow.",
    category=_HANDLE, since="1.0.0",
)
BUILTIN.define(
    501, "E", "Line {line} of the file '{path}' is not a correct event "
              "record.",
    cause="The line does not contain a JSON object that the library wrote.",
    remedy="Make sure that the file is a JSON Lines log file of this "
           "library. Remove the incorrect line.",
    category=_REPORT, since="1.0.0",
)

# -- Messages of version 1.1.0 ----------------------------------------------

_RUN = "Runs"
_CHECK = "Checks"

BUILTIN.define(
    320, "I", "{count} records of the message '{key}' were not recorded.",
    cause="A once, every or throttle method rejected records of the same "
          "message.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    330, "I", "Progress of '{operation}': {done} of {total} ({percent} %). "
              "Rate: {rate} per second. Time to completion: {eta} s.",
    cause="A progress object recorded the state of a long operation.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    331, "I", "The operation '{operation}' completed {done} items in "
              "{elapsed} s.",
    cause="A progress object came to its end.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    332, "W", "No progress of '{operation}' for {idle} s.",
    cause="The operation did not report progress in the permitted time. "
          "It is possibly blocked or very slow.",
    remedy="Examine the last records of the operation. Examine the load "
           "on the computer and the connected devices.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    333, "I", "The operation '{operation}' continued after {idle} s "
              "without progress.",
    cause="The operation reported progress again after a stall.",
    remedy="No action is necessary.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    340, "I", "The flight recorder wrote {count} earlier records because "
              "of an event of the severity {trigger}.",
    cause="An event with the trigger severity or higher occurred. The "
          "flight recorder then wrote the records that it kept in memory.",
    remedy="Read the earlier records to find what occurred before the "
           "event.",
    category=_HANDLE, since="1.1.0",
)
BUILTIN.define(
    401, "N", "The run '{run}' started.",
    cause="The program called the start_run function.",
    remedy="No action is necessary.",
    category=_RUN, since="1.1.0",
)
BUILTIN.define(
    402, "N", "The run '{run}' completed in {elapsed} s. Errors: {errors}. "
              "Warnings: {warnings}.",
    cause="The run came to its end.",
    remedy="If the number of errors is not 0, read the error records of "
           "the run.",
    category=_RUN, since="1.1.0",
)
BUILTIN.define(
    403, "E", "The run '{run}' stopped after {elapsed} s because of an "
              "exception: {exc_type}: {exc_message}",
    cause="The code of the run raised an exception and no code caught it.",
    remedy="Read the traceback in the log and correct the cause. Then "
           "start the run again.",
    category=_RUN, since="1.1.0",
)
BUILTIN.define(
    510, "E", "The log file '{path}' did not pass the integrity check. "
              "First problem: line {line}: {reason}",
    cause="A person or a program changed, removed or added a record after "
          "the library wrote the file. An incomplete last line after an "
          "abnormal stop also causes this message.",
    remedy="Do not use the file as evidence. Get a copy of the file from "
           "a backup and do the check again.",
    category=_REPORT, since="1.1.0",
)
BUILTIN.define(
    511, "E", "The log file '{path}' has no integrity data.",
    cause="The option file_chain was not set when the library wrote the "
          "file.",
    remedy="Set the option file_chain to true for future runs.",
    category=_REPORT, since="1.1.0",
)

_CHECK_TEXTS = (
    (1, "The value of '{name}' ({value}) is out of the range {minimum} to "
        "{maximum}.",
     "The value is less than the minimum or more than the maximum.",
     "Supply a value in the permitted range."),
    (2, "'{name}' contains {count} values that are not finite numbers.",
     "The data contain NaN or infinite values. A division by zero or an "
     "empty input is a usual cause.",
     "Examine the input data and the calculation that made the values."),
    (3, "'{name}' has the type {actual}. The permitted type is {expected}.",
     "The program gave a value of an incorrect type.",
     "Supply a value of the permitted type."),
    (4, "'{name}' is empty.",
     "The program gave an empty sequence, text or data set.",
     "Supply data that contain one or more items."),
    (5, "The value of '{name}' ({value}) is not one of the permitted "
        "values: {choices}.",
     "The value is not in the list of permitted values.",
     "Supply one of the permitted values."),
    (6, "The check '{name}' failed.",
     "A condition that the program examined was not true.",
     "Read the fields of the record to find the values that failed."),
)
for _number, _text, _cause, _remedy in _CHECK_TEXTS:
    BUILTIN.define(600 + _number, "E", _text, cause=_cause, remedy=_remedy,
                   category=_CHECK, since="1.1.0")
    BUILTIN.define(610 + _number, "W", _text, cause=_cause,
                   remedy=_remedy + " If the value is intended, no action "
                                    "is necessary.",
                   category=_CHECK, since="1.1.0")
