"""Formatters.

A formatter changes a log record into text. The module has three
formatters:

* :class:`PlainFormatter` writes one line of text for each event. It can
  add the cause, the remedy and the traceback on subsequent lines.
* :class:`ColourFormatter` writes the same text with ANSI colour codes.
* :class:`JsonFormatter` writes one JSON object on one line (JSON Lines).

Examples
--------
>>> import logging
>>> from annunciator.formatters import PlainFormatter
>>> from annunciator import Event, Severity
>>> event = Event(severity=Severity.ERROR, message="No beam",
...               code="APP-E-0001", logger="daq", fields={"run": 4})
>>> line = PlainFormatter().format_event(event)
>>> line.split(" ", 1)[1]
'ERROR    daq [APP-E-0001] No beam | run=4'
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List

from .events import Event
from .levels import Severity

__all__ = [
    "PlainFormatter",
    "ColourFormatter",
    "JsonFormatter",
    "supports_colour",
]

_RESET = "\x1b[0m"
_COLOURS: Dict[Severity, str] = {
    Severity.TRACE: "\x1b[2m",
    Severity.DEBUG: "\x1b[36m",
    Severity.INFO: "\x1b[32m",
    Severity.NOTICE: "\x1b[1;34m",
    Severity.WARNING: "\x1b[33m",
    Severity.ERROR: "\x1b[31m",
    Severity.CRITICAL: "\x1b[1;37;41m",
}


def supports_colour(stream: Any = None) -> bool:
    """Return ``True`` if a stream can show ANSI colour codes.

    The function returns ``False`` if the environment variable
    ``NO_COLOR`` is set or if the stream is not a terminal. On Windows,
    the function also sets the console to the virtual terminal mode.

    Parameters
    ----------
    stream
        The stream to examine. The default is ``sys.stderr``.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = sys.stderr if stream is None else stream
    try:
        if not stream.isatty():
            return False
    except Exception:  # noqa: BLE001 - a stream without isatty
        return False
    if os.name == "nt":  # pragma: no cover - Windows only
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            for handle_id in (-11, -12):
                handle = kernel32.GetStdHandle(handle_id)
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:  # noqa: BLE001
            return False
    return True


def _format_value(value: Any) -> str:
    """Return a field value as short text."""
    if isinstance(value, str):
        if value == "" or any(char.isspace() for char in value) or "=" in value:
            return repr(value)
        return value
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    if len(text) > 120:
        text = text[:117] + "..."
    return text


class PlainFormatter(logging.Formatter):
    """Formatter that writes readable text.

    The first line has this structure::

        TIME SEVERITY LOGGER [CODE] MESSAGE | KEY=VALUE ...

    Parameters
    ----------
    utc
        If ``True``, write the time in UTC with the suffix ``Z``. If
        ``False``, write the local time with its UTC offset.
    show_fields
        If ``True``, add the structured fields to the first line.
    show_help
        If ``True``, add the cause and the remedy for events that have
        the severity ``WARNING`` or higher.
    show_source
        If ``True``, add the source file and the line number.
    show_traceback
        If ``True``, add the traceback of a related exception.
    """

    def __init__(
        self,
        *,
        utc: bool = True,
        show_fields: bool = True,
        show_help: bool = True,
        show_source: bool = False,
        show_traceback: bool = True,
    ) -> None:
        super().__init__()
        self.utc = utc
        self.show_fields = show_fields
        self.show_help = show_help
        self.show_source = show_source
        self.show_traceback = show_traceback

    def format(self, record: logging.LogRecord) -> str:
        """Return the text for a record of the :mod:`logging` module."""
        text = self.format_event(Event.from_record(record))
        if record.stack_info:
            text = f"{text}\n{record.stack_info}"
        return text

    def _paint(self, severity: Severity, text: str) -> str:
        """Return the text. A subclass can add colour codes."""
        return text

    def _timestamp(self, event: Event) -> str:
        if self.utc:
            return event.to_dict()["timestamp"]
        return event.timestamp.astimezone().isoformat(timespec="milliseconds")

    def format_event(self, event: Event) -> str:
        """Return the text for an event.

        Parameters
        ----------
        event
            The event to format.
        """
        head: List[str] = [
            self._timestamp(event),
            self._paint(event.severity, f"{event.severity.name:<8}"),
        ]
        if event.logger:
            head.append(event.logger)
        if event.code:
            head.append(f"[{event.code}]")
        head.append(event.message)
        line = " ".join(head)
        if self.show_fields and event.fields:
            pairs = " ".join(
                f"{key}={_format_value(value)}"
                for key, value in event.fields.items()
            )
            line = f"{line} | {pairs}"
        if self.show_source and event.source is not None:
            line = (
                f"{line} ({os.path.basename(event.source.file)}:"
                f"{event.source.line})"
            )
        lines = [line]
        if self.show_help and event.severity.is_problem:
            if event.cause:
                lines.append(f"    Cause:  {event.cause}")
            if event.remedy:
                lines.append(f"    Remedy: {event.remedy}")
        if (
            self.show_traceback
            and event.exception is not None
            and event.exception.traceback
        ):
            for row in event.exception.traceback.splitlines():
                lines.append(f"    {row}")
            if event.exception.fingerprint:
                lines.append(f"    Fingerprint: {event.exception.fingerprint}")
            for label, values in (event.exception.locals or {}).items():
                lines.append(f"    Local variables of {label}:")
                for name, value in values.items():
                    lines.append(f"        {name} = {value}")
        return "\n".join(lines)


class ColourFormatter(PlainFormatter):
    """Formatter that writes readable text with ANSI colour codes.

    The formatter adds colour only to the severity name. The parameters
    are the same as the parameters of :class:`PlainFormatter`.
    """

    def _paint(self, severity: Severity, text: str) -> str:
        return f"{_COLOURS.get(severity, '')}{text}{_RESET}"


class JsonFormatter(logging.Formatter):
    """Formatter that writes one JSON object on one line.

    The object has the structure that
    :meth:`annunciator.events.Event.to_dict` returns. A file of these
    lines is a JSON Lines file. The report functions and the
    command-line interface can read such a file.

    Parameters
    ----------
    include_source
        If ``True``, include the source position in each object.
    """

    def __init__(self, *, include_source: bool = True) -> None:
        super().__init__()
        self.include_source = include_source

    def format(self, record: logging.LogRecord) -> str:
        """Return the JSON text for a record."""
        event = Event.from_record(record)
        if not self.include_source:
            event.source = None
        if record.stack_info:
            event.fields.setdefault("stack", record.stack_info)
        return event.to_json()
