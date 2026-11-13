"""Structured loggers.

A :class:`StructuredLogger` is a thin layer on a logger of the standard
:mod:`logging` module. It adds message codes, structured fields and
context data to each record.

Use :func:`get_logger` to get a structured logger.

Examples
--------
>>> from annunciator import get_logger
>>> log = get_logger("demo.module")
>>> log.name
'demo.module'
>>> child = log.bind(sample="S-1")
>>> child.bound
{'sample': 'S-1'}
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Mapping, Optional, Tuple

from .catalogue import lookup
from .context import get_context
from .levels import Severity, SeverityLike

__all__ = [
    "StructuredLogger",
    "get_logger",
    "suppressed_counts",
    "record_suppressed_summary",
    "reset_occurrences",
]

#: Code that the library uses for an exception that has no message code.
_UNCODED_EXCEPTION = "ANN-E-0303"
_LOGGED_FLAG = "_annunciator_logged"

# State of the once, every and throttle methods.
# key -> [number of calls, time of the last record, rejected since then, total]
_OCCURRENCES: Dict[str, list] = {}
_OCCURRENCES_LOCK = threading.Lock()


def suppressed_counts() -> Dict[str, int]:
    """Return the number of rejected records for each message key.

    The methods ``once``, ``every`` and ``throttle`` of
    :class:`StructuredLogger` reject records. The dictionary contains
    only the keys that have one or more rejected records.
    """
    with _OCCURRENCES_LOCK:
        return {key: item[3] for key, item in _OCCURRENCES.items() if item[3]}


def reset_occurrences() -> None:
    """Remove the state of the methods ``once``, ``every`` and ``throttle``.

    After this call, ``once`` records its message again.
    """
    with _OCCURRENCES_LOCK:
        _OCCURRENCES.clear()


def record_suppressed_summary(logger: Optional["StructuredLogger"] = None) -> int:
    """Record one event for each message that has rejected records.

    The function records the code ``ANN-I-0320``. Then it sets the
    counts to zero. The functions
    :func:`~annunciator.config.shutdown` and
    :meth:`~annunciator.provenance.Run.finish` call this function.

    Parameters
    ----------
    logger
        The logger for the records. The default is the logger
        ``annunciator``.

    Returns
    -------
    int
        The number of events that the function recorded.
    """
    log = logger if logger is not None else get_logger("annunciator")
    with _OCCURRENCES_LOCK:
        pending = {key: item[3] for key, item in _OCCURRENCES.items() if item[3]}
        for item in _OCCURRENCES.values():
            item[3] = 0
    for key, count in pending.items():
        log.event("ANN-I-0320", count=count, key=key)
    return len(pending)


class StructuredLogger:
    """Logger that records messages with codes and structured fields.

    Do not make an instance directly. Use :func:`get_logger`.

    Parameters
    ----------
    logger
        The logger of the :mod:`logging` module that receives the
        records.
    bound
        Fields that the logger adds to each record.

    Notes
    -----
    Each log method accepts keyword arguments. The logger records these
    arguments as structured fields. The keywords ``exc_info``,
    ``stack_info`` and ``stacklevel`` have the same function as in the
    :mod:`logging` module.
    """

    def __init__(
        self,
        logger: logging.Logger,
        bound: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._logger = logger
        self._bound: Dict[str, Any] = dict(bound or {})

    def __repr__(self) -> str:
        return f"StructuredLogger({self.name!r}, bound={self._bound!r})"

    # -- properties --------------------------------------------------------

    @property
    def name(self) -> str:
        """The name of the logger."""
        return self._logger.name

    @property
    def stdlib(self) -> logging.Logger:
        """The related logger of the :mod:`logging` module."""
        return self._logger

    @property
    def bound(self) -> Dict[str, Any]:
        """A copy of the fields that the logger adds to each record."""
        return dict(self._bound)

    # -- configuration -----------------------------------------------------

    def bind(self, **fields: Any) -> "StructuredLogger":
        """Return a new logger that adds the given fields to each record.

        The initial logger does not change.
        """
        merged = dict(self._bound)
        merged.update(fields)
        return StructuredLogger(self._logger, merged)

    def set_level(self, severity: SeverityLike) -> None:
        """Set the minimum severity that the logger records."""
        self._logger.setLevel(int(Severity.coerce(severity)))

    def is_enabled_for(self, severity: SeverityLike) -> bool:
        """Return ``True`` if the logger records the given severity."""
        return self._logger.isEnabledFor(int(Severity.coerce(severity)))

    # -- core --------------------------------------------------------------

    def _emit(
        self,
        severity: Severity,
        message: str,
        args: Tuple[Any, ...],
        *,
        code: Optional[str] = None,
        fields: Optional[Mapping[str, Any]] = None,
        cause: str = "",
        remedy: str = "",
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
    ) -> None:
        """Send one record to the :mod:`logging` module."""
        level = int(severity)
        if not self._logger.isEnabledFor(level):
            return
        merged = dict(self._bound)
        if fields:
            merged.update(fields)
        extra = {
            "ann_code": code,
            "ann_fields": merged,
            "ann_context": get_context(),
            "ann_cause": cause,
            "ann_remedy": remedy,
        }
        # stacklevel 1 identifies the caller of _emit.
        self._logger.log(
            level,
            message,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel + 1,
            extra=extra,
        )

    def log(
        self,
        severity: SeverityLike,
        message: str,
        *args: Any,
        code: Optional[str] = None,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        **fields: Any,
    ) -> None:
        """Record a message with the given severity.

        Parameters
        ----------
        severity
            The severity of the message.
        message
            The message text. The text can contain ``%`` format
            specifiers for ``args``.
        *args
            The values for the ``%`` format specifiers.
        code
            An optional message code. If the code has a definition, the
            logger adds the cause and the remedy of the definition.
        exc_info
            ``True``, an exception or an exception tuple. The logger
            then records the traceback.
        stack_info
            If ``True``, record the call stack.
        stacklevel
            The number of stack frames between this call and the line
            that the record must identify.
        **fields
            Structured fields for the record.
        """
        definition = lookup(code)
        self._emit(
            Severity.coerce(severity),
            message,
            args,
            code=code,
            fields=fields,
            cause=definition.cause if definition else "",
            remedy=definition.remedy if definition else "",
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel + 1,
        )

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``TRACE``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.TRACE, message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``DEBUG``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``INFO``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.INFO, message, *args, **kwargs)

    def notice(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``NOTICE``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.NOTICE, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``WARNING``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``ERROR``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record a message with the severity ``CRITICAL``."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(Severity.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Record an ``ERROR`` message with the current traceback.

        Call this method only in an ``except`` block.
        """
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        kwargs.setdefault("exc_info", True)
        self.log(Severity.ERROR, message, *args, **kwargs)

    # -- repeated messages -------------------------------------------------

    def _occurrence(self, key: Optional[str], message: str, code: Optional[str]):
        name = key or f"{self.name}:{code or message}"
        with _OCCURRENCES_LOCK:
            item = _OCCURRENCES.setdefault(name, [0, None, 0, 0])
            item[0] += 1
        return item

    def once(
        self,
        severity: SeverityLike,
        message: str,
        *args: Any,
        key: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Record a message only the first time.

        Use this method for a condition that the user must know about
        one time, for example a default value that the program applied.

        Parameters
        ----------
        severity
            The severity of the message.
        message
            The message text.
        *args
            The values for the ``%`` format specifiers.
        key
            The identifier of the message. The default is the logger
            name with the code or the message text.
        **kwargs
            The other parameters of :meth:`log`.

        Returns
        -------
        bool
            ``True`` if the logger recorded the message.
        """
        item = self._occurrence(key, message, kwargs.get("code"))
        if item[0] > 1:
            with _OCCURRENCES_LOCK:
                item[3] += 1
            return False
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        self.log(severity, message, *args, **kwargs)
        return True

    def every(
        self,
        interval: int,
        severity: SeverityLike,
        message: str,
        *args: Any,
        key: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Record a message on the first call and then on each n-th call.

        The logger adds the field ``occurrence`` with the number of the
        call.

        Parameters
        ----------
        interval
            The number of calls between two records. The minimum is 1.
        severity
            The severity of the message.
        message
            The message text.
        *args
            The values for the ``%`` format specifiers.
        key
            The identifier of the message.
        **kwargs
            The other parameters of :meth:`log`.

        Returns
        -------
        bool
            ``True`` if the logger recorded the message.
        """
        item = self._occurrence(key, message, kwargs.get("code"))
        if (item[0] - 1) % max(int(interval), 1) != 0:
            with _OCCURRENCES_LOCK:
                item[3] += 1
            return False
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        kwargs.setdefault("occurrence", item[0])
        self.log(severity, message, *args, **kwargs)
        return True

    def throttle(
        self,
        seconds: float,
        severity: SeverityLike,
        message: str,
        *args: Any,
        key: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Record a message a maximum of one time in a time interval.

        When the logger records the message again, it adds the field
        ``suppressed`` with the number of rejected records.

        Parameters
        ----------
        seconds
            The minimum time between two records.
        severity
            The severity of the message.
        message
            The message text.
        *args
            The values for the ``%`` format specifiers.
        key
            The identifier of the message.
        **kwargs
            The other parameters of :meth:`log`.

        Returns
        -------
        bool
            ``True`` if the logger recorded the message.
        """
        item = self._occurrence(key, message, kwargs.get("code"))
        now = time.monotonic()
        with _OCCURRENCES_LOCK:
            if item[1] is not None and now - item[1] < seconds:
                item[2] += 1
                item[3] += 1
                return False
            rejected, item[1], item[2] = item[2], now, 0
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        if rejected:
            kwargs.setdefault("suppressed", rejected)
        self.log(severity, message, *args, **kwargs)
        return True

    # -- catalogue messages ------------------------------------------------

    def event(
        self,
        code: str,
        *,
        strict: bool = False,
        exc_info: Any = None,
        stacklevel: int = 1,
        **fields: Any,
    ) -> None:
        """Record a message from a message catalogue.

        The logger gets the severity, the text, the cause and the remedy
        from the definition of the code.

        Parameters
        ----------
        code
            The message code.
        strict
            If ``True``, raise an exception when the code has no
            definition. If ``False``, record an ``ERROR`` message that
            contains the code and the fields.
        exc_info
            ``True``, an exception or an exception tuple.
        stacklevel
            The number of stack frames between this call and the line
            that the record must identify.
        **fields
            The values for the replacement fields. The logger also
            records them as structured fields.

        Raises
        ------
        CatalogueError
            If ``strict`` is ``True`` and the code has no definition
            (``ANN-E-0103``).
        """
        definition = lookup(code)
        if definition is None:
            if strict:
                from .errors import CatalogueError

                raise CatalogueError(code="ANN-E-0103", item=code)
            self._emit(
                Severity.ERROR,
                "Message code %s has no definition in a registered catalogue.",
                (code,),
                code=code,
                fields=fields,
                exc_info=exc_info,
                stacklevel=stacklevel + 1,
            )
            return
        self._emit(
            definition.severity,
            definition.format(**fields),
            (),
            code=code,
            fields=fields,
            cause=definition.cause,
            remedy=definition.remedy,
            exc_info=exc_info,
            stacklevel=stacklevel + 1,
        )

    def report(
        self,
        exc: BaseException,
        *,
        severity: Optional[SeverityLike] = None,
        operation: str = "",
        traceback: bool = True,
        force: bool = False,
        stacklevel: int = 1,
        **fields: Any,
    ) -> bool:
        """Record an exception as an event.

        For a coded exception, the logger uses the code, the text, the
        cause, the remedy, the fields and the context of the exception.
        For all other exceptions, the logger uses the code
        ``ANN-E-0303``.

        The logger records each exception object only one time. Thus an
        exception that goes through two handlers does not make two
        records.

        Parameters
        ----------
        exc
            The exception.
        severity
            The severity of the record. The default is the severity of
            the exception, or ``ERROR``.
        operation
            The name of the operation that failed.
        traceback
            If ``True``, record the traceback.
        force
            If ``True``, record the exception again when a logger
            already recorded it.
        stacklevel
            The number of stack frames between this call and the line
            that the record must identify.
        **fields
            More structured fields for the record.

        Returns
        -------
        bool
            ``True`` if the logger made a record.
        """
        if getattr(exc, _LOGGED_FLAG, False) and not force:
            return False
        exc_info = (type(exc), exc, exc.__traceback__) if traceback else None
        merged: Dict[str, Any] = {}
        if operation:
            merged["operation"] = operation
        code = getattr(exc, "code", None)
        if code and hasattr(exc, "message"):
            merged.update(getattr(exc, "fields", {}) or {})
            merged.update(getattr(exc, "context", {}) or {})
            merged.update(fields)
            level = Severity.coerce(
                severity if severity is not None else getattr(exc, "severity", 40)
            )
            self._emit(
                level,
                str(exc.message),  # type: ignore[attr-defined]
                (),
                code=code,
                fields=merged,
                cause=getattr(exc, "cause", "") or "",
                remedy=getattr(exc, "remedy", "") or "",
                exc_info=exc_info,
                stacklevel=stacklevel + 1,
            )
        else:
            definition = lookup(_UNCODED_EXCEPTION)
            assert definition is not None
            merged.update(getattr(exc, "context", {}) or {})
            merged.update(fields)
            values = {
                "operation": operation or "(not named)",
                "exc_type": type(exc).__qualname__,
                "exc_message": str(exc),
            }
            merged.setdefault("exc_type", values["exc_type"])
            self._emit(
                Severity.coerce(severity if severity is not None else 40),
                definition.format(**values),
                (),
                code=_UNCODED_EXCEPTION,
                fields=merged,
                cause=definition.cause,
                remedy=definition.remedy,
                exc_info=exc_info,
                stacklevel=stacklevel + 1,
            )
        try:
            setattr(exc, _LOGGED_FLAG, True)
        except Exception:  # noqa: BLE001 - some exceptions have no __dict__
            pass
        return True


_LOGGERS: Dict[str, StructuredLogger] = {}
_LOGGERS_LOCK = threading.Lock()


def get_logger(name: Optional[str] = None) -> StructuredLogger:
    """Return the structured logger that has the given name.

    The function returns the same object each time for the same name.

    Parameters
    ----------
    name
        The name of the logger. Use ``__name__`` in a module. If you
        give ``None``, the function returns the root logger.

    Returns
    -------
    StructuredLogger
        The logger.
    """
    key = name or ""
    with _LOGGERS_LOCK:
        logger = _LOGGERS.get(key)
        if logger is None:
            logger = StructuredLogger(logging.getLogger(name))
            _LOGGERS[key] = logger
    return logger
