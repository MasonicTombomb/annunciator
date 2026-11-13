"""Handlers.

A handler sends log records to a destination. This module adds four
handlers to the handlers of the standard :mod:`logging` module:

* :class:`ConsoleHandler` writes to the current ``sys.stdout`` or
  ``sys.stderr``.
* :class:`EventStoreHandler` keeps the last events in memory.
* :class:`CallbackHandler` gives each event to a function.
* :class:`AsyncQueueHandler` puts records in a queue for a different
  thread.

Examples
--------
>>> import logging
>>> from annunciator.handlers import EventStoreHandler
>>> store = EventStoreHandler(capacity=10)
>>> logger = logging.getLogger("doctest.handlers")
>>> logger.addHandler(store)
>>> logger.propagate = False
>>> logger.warning("Low pressure")
>>> [event.message for event in store.events]
['Low pressure']
>>> store.counts()
{'WARNING': 1}
"""

from __future__ import annotations

import collections
import copy
import logging
import logging.handlers
import sys
import threading
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Union

from .context import get_context
from .events import Event, ExceptionInfo
from .levels import Severity, SeverityLike

__all__ = [
    "ConsoleHandler",
    "EventStoreHandler",
    "CallbackHandler",
    "AsyncQueueHandler",
    "make_file_handler",
]


class ConsoleHandler(logging.StreamHandler):
    """Handler that writes to the current standard stream.

    The handler finds ``sys.stdout`` or ``sys.stderr`` each time it
    writes. Thus it operates correctly when a test tool or a notebook
    replaces the standard streams.

    Parameters
    ----------
    stream_name
        ``"stdout"`` or ``"stderr"``.
    """

    def __init__(self, stream_name: str = "stderr") -> None:
        if stream_name not in ("stdout", "stderr"):
            raise ValueError("stream_name must be 'stdout' or 'stderr'")
        self.stream_name = stream_name
        super().__init__()

    @property
    def stream(self):  # type: ignore[override]
        """The current standard stream."""
        return getattr(sys, self.stream_name)

    @stream.setter
    def stream(self, value) -> None:
        # The standard stream is always found at the time of use.
        pass


class EventStoreHandler(logging.Handler):
    """Handler that keeps the last events in memory.

    Use the store to make a summary at the end of a program. You can
    also show the events in a graphical user interface or examine them
    in a test.

    Parameters
    ----------
    capacity
        The maximum number of events. When the store is full, the
        handler removes the oldest event.
    level
        The minimum severity that the handler keeps.
    """

    def __init__(
        self, capacity: int = 1000, level: SeverityLike = Severity.TRACE
    ) -> None:
        super().__init__(int(Severity.coerce(level)))
        self.capacity = int(capacity)
        self._events: Deque[Event] = collections.deque(maxlen=self.capacity)
        self._counts: Dict[str, int] = {}
        self._store_lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """Add the event of a record to the store."""
        try:
            event = Event.from_record(record)
            with self._store_lock:
                self._events.append(event)
                name = event.severity.name
                self._counts[name] = self._counts.get(name, 0) + 1
        except Exception:  # noqa: BLE001
            self.handleError(record)

    @property
    def events(self) -> List[Event]:
        """A list of the events in the store, oldest first."""
        with self._store_lock:
            return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def counts(self) -> Dict[str, int]:
        """Return the number of events for each severity name.

        The numbers include the events that the handler removed because
        the store was full.
        """
        with self._store_lock:
            return dict(self._counts)

    def select(
        self,
        *,
        minimum: Optional[SeverityLike] = None,
        code: Optional[str] = None,
        logger: Optional[str] = None,
    ) -> List[Event]:
        """Return the events that agree with all given conditions.

        Parameters
        ----------
        minimum
            Keep only the events of this severity or higher.
        code
            Keep only the events that have this message code.
        logger
            Keep only the events of this logger and of its children.
        """
        result = []
        floor = None if minimum is None else Severity.coerce(minimum)
        for event in self.events:
            if floor is not None and event.severity < floor:
                continue
            if code is not None and event.code != code:
                continue
            if logger is not None and not (
                event.logger == logger or event.logger.startswith(logger + ".")
            ):
                continue
            result.append(event)
        return result

    def clear(self) -> None:
        """Remove all events and set all counts to zero."""
        with self._store_lock:
            self._events.clear()
            self._counts.clear()


class CallbackHandler(logging.Handler):
    """Handler that gives each event to a function.

    Use this handler to send events to a status bar, a message queue or
    an alarm system.

    Parameters
    ----------
    callback
        A function that accepts one :class:`~annunciator.events.Event`.
    level
        The minimum severity that the handler sends.

    Notes
    -----
    If the function raises an exception, the handler uses the standard
    error procedure of the :mod:`logging` module. The exception does not
    stop the program.
    """

    def __init__(
        self,
        callback: Callable[[Event], None],
        level: SeverityLike = Severity.TRACE,
    ) -> None:
        super().__init__(int(Severity.coerce(level)))
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Give the event of a record to the function."""
        try:
            self.callback(Event.from_record(record))
        except Exception:  # noqa: BLE001
            self.handleError(record)


class AsyncQueueHandler(logging.handlers.QueueHandler):
    """Queue handler that keeps the structured data of each record.

    The standard queue handler changes the exception data into text.
    This handler keeps the exception data and the context data. Thus the
    handlers on the other side of the queue can write complete events.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        """Make a record that is safe to give to a different thread."""
        record = copy.copy(record)
        if getattr(record, "ann_context", None) is None:
            record.ann_context = get_context()
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            record.ann_exception = ExceptionInfo.from_exception(exc)
            if getattr(record, "ann_code", None) is None and getattr(exc, "code", None):
                record.ann_code = exc.code
                record.ann_cause = getattr(exc, "cause", "")
                record.ann_remedy = getattr(exc, "remedy", "")
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            message = str(record.msg)
        record.msg = message
        record.message = message
        record.args = None
        record.exc_info = None
        record.exc_text = None
        return record


def make_file_handler(
    path: Union[str, Path],
    *,
    rotate: str = "size",
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
    when: str = "midnight",
    encoding: str = "utf-8",
    utc: bool = True,
) -> logging.Handler:
    """Make a file handler with the selected rotation.

    The function makes the parent directory if it does not exist.

    Parameters
    ----------
    path
        The path of the log file.
    rotate
        ``"none"``, ``"size"`` or ``"time"``.
    max_bytes
        For ``"size"``: the maximum size of the file in bytes.
    backup_count
        The number of old files to keep.
    when
        For ``"time"``: the rotation interval of
        :class:`logging.handlers.TimedRotatingFileHandler`.
    encoding
        The text encoding of the file.
    utc
        For ``"time"``: if ``True``, use UTC for the rotation time.

    Returns
    -------
    logging.Handler
        The file handler.

    Raises
    ------
    ValueError
        If ``rotate`` is not a permitted value.
    """
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    if rotate == "none":
        return logging.FileHandler(file, encoding=encoding, delay=True)
    if rotate == "size":
        return logging.handlers.RotatingFileHandler(
            file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
            delay=True,
        )
    if rotate == "time":
        return logging.handlers.TimedRotatingFileHandler(
            file,
            when=when,
            backupCount=backup_count,
            encoding=encoding,
            utc=utc,
            delay=True,
        )
    raise ValueError("rotate must be 'none', 'size' or 'time'")
