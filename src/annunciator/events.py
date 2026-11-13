"""Event records.

An :class:`Event` is the structured form of one log record. The JSON
formatter, the event store and the report functions use this class.

Examples
--------
>>> from annunciator import Event, Severity
>>> event = Event(severity=Severity.WARNING, message="Low count rate",
...               code="APP-W-0003", fields={"rate": 1.5})
>>> data = event.to_dict()
>>> data["severity"], data["code"], data["fields"]
('WARNING', 'APP-W-0003', {'rate': 1.5})
>>> Event.from_dict(data).message
'Low count rate'
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from .context import get_context
from .levels import Severity

__all__ = ["Event", "ExceptionInfo", "SourceLocation", "json_default", "fingerprint"]

_UTC = _dt.timezone.utc


def _now() -> _dt.datetime:
    return _dt.datetime.now(_UTC)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def json_default(value: Any) -> Any:
    """Convert a value that JSON cannot contain to a value that it can.

    The function converts dates to ISO 8601 text, sets to sorted lists,
    and bytes to hexadecimal text. It converts all other types to their
    :func:`str` form.
    """
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        try:
            return sorted(value)
        except TypeError:
            return [str(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    if isinstance(value, Severity):
        return value.name
    return str(value)


def fingerprint(type_name: str, tb: Any) -> str:
    """Return a short identifier for a type of failure.

    Two exceptions have the same fingerprint if they have the same class
    and the same sequence of functions in the traceback. The line numbers
    and the message text have no effect. Thus you can count how many
    times the same failure occurred.

    Parameters
    ----------
    type_name
        The name of the exception class.
    tb
        The traceback object, or ``None``.

    Returns
    -------
    str
        Twelve hexadecimal characters.
    """
    parts = [type_name]
    for frame, _ in traceback.walk_tb(tb):
        code = frame.f_code
        parts.append(f"{os.path.basename(code.co_filename)}:{code.co_name}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]


@dataclass(frozen=True)
class SourceLocation:
    """The position in the source code that made an event.

    Parameters
    ----------
    file
        The path of the source file.
    line
        The line number.
    function
        The name of the function.
    module
        The name of the module.
    """

    file: str = ""
    line: int = 0
    function: str = ""
    module: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return the location as a dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "module": self.module,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceLocation":
        """Make a location from a dictionary."""
        return cls(
            file=str(data.get("file", "")),
            line=int(data.get("line", 0) or 0),
            function=str(data.get("function", "")),
            module=str(data.get("module", "")),
        )


@dataclass(frozen=True)
class ExceptionInfo:
    """Data about an exception that is related to an event.

    Parameters
    ----------
    type
        The name of the exception class.
    message
        The text of the exception.
    traceback
        The traceback text, or ``None``.
    fingerprint
        The identifier of the type of failure. Refer to
        :func:`fingerprint`.
    locals
        The local variables of the last frames, or ``None``. The keys
        identify the frames. The option ``capture_locals`` controls
        this item.
    """

    type: str
    message: str
    traceback: Optional[str] = None
    fingerprint: str = ""
    locals: Optional[Dict[str, Dict[str, str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return the data as a dictionary without empty items."""
        data: Dict[str, Any] = {"type": self.type, "message": self.message}
        if self.fingerprint:
            data["fingerprint"] = self.fingerprint
        if self.traceback:
            data["traceback"] = self.traceback
        if self.locals:
            data["locals"] = self.locals
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExceptionInfo":
        """Make the data object from a dictionary."""
        return cls(
            type=str(data.get("type", "")),
            message=str(data.get("message", "")),
            traceback=data.get("traceback"),
            fingerprint=str(data.get("fingerprint", "")),
            locals=data.get("locals"),
        )

    @classmethod
    def from_exception(
        cls, exc: BaseException, *, with_traceback: bool = True
    ) -> "ExceptionInfo":
        """Make the data object from an exception.

        Parameters
        ----------
        exc
            The exception.
        with_traceback
            If ``True``, include the traceback text.
        """
        text = None
        if with_traceback:
            text = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).rstrip()
        name = type(exc).__qualname__
        return cls(
            type=name,
            message=str(exc),
            traceback=text,
            fingerprint=fingerprint(name, exc.__traceback__),
        )


@dataclass
class Event:
    """One event that the library recorded.

    Parameters
    ----------
    severity
        The severity of the event.
    message
        The message text.
    code
        The message code, or ``None``.
    logger
        The name of the logger that recorded the event.
    fields
        The structured data of the event. The context data are included.
    cause
        The probable cause.
    remedy
        The corrective action.
    exception
        Data about a related exception.
    source
        The position in the source code.
    timestamp
        The time of the event. The time zone is UTC.
    process
        The identifier of the process.
    thread
        The name of the thread.
    event_id
        A unique identifier of the event.
    """

    severity: Severity
    message: str
    code: Optional[str] = None
    logger: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    cause: str = ""
    remedy: str = ""
    exception: Optional[ExceptionInfo] = None
    source: Optional[SourceLocation] = None
    timestamp: _dt.datetime = field(default_factory=_now)
    process: int = field(default_factory=os.getpid)
    thread: str = ""
    event_id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        self.severity = Severity.coerce(self.severity)

    # -- conversion --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return the event as a dictionary.

        The dictionary does not contain empty items. The time is an
        ISO 8601 text in UTC with the suffix ``Z``.
        """
        stamp = self.timestamp.astimezone(_UTC)
        data: Dict[str, Any] = {
            "timestamp": stamp.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            "severity": self.severity.name,
            "level": int(self.severity),
            "code": self.code,
            "logger": self.logger,
            "message": self.message,
            "fields": dict(self.fields),
            "cause": self.cause,
            "remedy": self.remedy,
            "exception": self.exception.to_dict() if self.exception else None,
            "source": self.source.to_dict() if self.source else None,
            "process": self.process,
            "thread": self.thread,
            "event_id": self.event_id,
        }
        return {
            key: value
            for key, value in data.items()
            if value not in (None, "", {})
        }

    def to_json(self) -> str:
        """Return the event as one line of JSON text."""
        return json.dumps(
            self.to_dict(), default=json_default, ensure_ascii=False
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Event":
        """Make an event from a dictionary.

        The dictionary must have the structure that :meth:`to_dict`
        returns.

        Raises
        ------
        ValueError
            If the dictionary does not contain a severity and a message.
        """
        if "message" not in data or not ("severity" in data or "level" in data):
            raise ValueError("an event record must have a severity and a message")
        stamp = data.get("timestamp")
        if isinstance(stamp, str):
            timestamp = _dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=_UTC)
        elif isinstance(stamp, _dt.datetime):
            timestamp = stamp
        else:
            timestamp = _now()
        exception = data.get("exception")
        source = data.get("source")
        return cls(
            severity=Severity.coerce(data.get("severity", data.get("level"))),
            message=str(data["message"]),
            code=data.get("code"),
            logger=str(data.get("logger", "")),
            fields=dict(data.get("fields", {}) or {}),
            cause=str(data.get("cause", "")),
            remedy=str(data.get("remedy", "")),
            exception=ExceptionInfo.from_dict(exception) if exception else None,
            source=SourceLocation.from_dict(source) if source else None,
            timestamp=timestamp,
            process=int(data.get("process", 0) or 0),
            thread=str(data.get("thread", "")),
            event_id=str(data.get("event_id", "")) or _new_id(),
        )

    @classmethod
    def from_json(cls, text: str) -> "Event":
        """Make an event from one line of JSON text."""
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("an event record must be a JSON object")
        return cls.from_dict(data)

    @classmethod
    def from_record(cls, record: logging.LogRecord) -> "Event":
        """Make an event from a record of the :mod:`logging` module.

        The method reads the attributes that
        :class:`~annunciator.logger.StructuredLogger` adds to the record.
        It also accepts records from standard loggers. If the record has
        a coded exception and no message code, the method uses the code,
        the cause and the remedy of the exception.
        """
        fields: Dict[str, Any] = {}
        ctx = getattr(record, "ann_context", None)
        fields.update(get_context() if ctx is None else ctx)
        fields.update(getattr(record, "ann_fields", None) or {})
        code = getattr(record, "ann_code", None)
        cause = getattr(record, "ann_cause", "") or ""
        remedy = getattr(record, "ann_remedy", "") or ""

        exception = getattr(record, "ann_exception", None)
        captured = getattr(record, "ann_locals", None)
        if exception is not None and captured and not exception.locals:
            exception = ExceptionInfo(
                exception.type, exception.message, exception.traceback,
                exception.fingerprint, captured,
            )
        exc_info = record.exc_info
        if exception is None and exc_info and exc_info[1] is not None:
            exc = exc_info[1]
            if not record.exc_text:
                record.exc_text = "".join(
                    traceback.format_exception(*exc_info)
                ).rstrip()
            name = type(exc).__qualname__
            exception = ExceptionInfo(
                type=name,
                message=str(exc),
                traceback=record.exc_text,
                fingerprint=fingerprint(name, exc_info[2]),
                locals=getattr(record, "ann_locals", None),
            )
            if code is None and getattr(exc, "code", None):
                code = exc.code
                cause = cause or getattr(exc, "cause", "") or ""
                remedy = remedy or getattr(exc, "remedy", "") or ""
            extra = getattr(exc, "context", None)
            if isinstance(extra, dict):
                for key, value in extra.items():
                    fields.setdefault(key, value)

        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never fail in a log call
            message = str(record.msg)

        return cls(
            severity=Severity.coerce(record.levelno),
            message=message,
            code=code,
            logger=record.name,
            fields=fields,
            cause=cause,
            remedy=remedy,
            exception=exception,
            source=SourceLocation(
                file=record.pathname,
                line=record.lineno,
                function=record.funcName or "",
                module=record.module,
            ),
            timestamp=_dt.datetime.fromtimestamp(record.created, _UTC),
            process=record.process or 0,
            thread=record.threadName or "",
        )
