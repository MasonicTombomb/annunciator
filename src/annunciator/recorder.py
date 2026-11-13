"""Flight recorder.

A flight recorder keeps the last detailed records in memory. It writes
them only when an event of a trigger severity occurs. Thus the log of a
normal run stays short. The log of a failed run contains the detailed
records that came before the failure.

The option ``flight_recorder`` of the configuration installs a flight
recorder on the log file. If the configuration has no log file, the
flight recorder is on the console.

Examples
--------
>>> import logging
>>> from annunciator.handlers import EventStoreHandler
>>> from annunciator.recorder import FlightRecorderHandler
>>> target = EventStoreHandler()
>>> target.setLevel(logging.WARNING)
>>> recorder = FlightRecorderHandler(target, capacity=50)
>>> logger = logging.getLogger("doctest.recorder")
>>> logger.propagate = False
>>> logger.setLevel(logging.DEBUG)
>>> logger.addHandler(recorder)
>>> logger.debug("step 1")
>>> logger.debug("step 2")
>>> len(target.events)
0
>>> logger.error("failure")
>>> [event.message for event in target.events][1:]
['step 1', 'step 2', 'failure']
"""

from __future__ import annotations

import collections
import logging
from typing import Deque

from .catalogue import lookup
from .levels import Severity, SeverityLike

__all__ = ["FlightRecorderHandler"]


class FlightRecorderHandler(logging.Handler):
    """Handler that keeps detailed records until a failure occurs.

    The handler sends each record of the target severity directly to
    the target handler. It keeps all lower records in memory. When a
    record of the trigger severity or higher comes, the handler first
    sends the kept records to the target. Each of these records has the
    field ``flight_recorder`` with the value ``True``.

    Parameters
    ----------
    target
        The handler that writes the records. Its level is the target
        severity.
    capacity
        The maximum number of records in memory. When the memory is
        full, the handler removes the oldest record.
    trigger
        The severity that causes the handler to write the kept records.
    capture_level
        The minimum severity of the records that the handler keeps.

    Attributes
    ----------
    flushes : int
        The number of times that the handler wrote the kept records.
    """

    def __init__(
        self,
        target: logging.Handler,
        capacity: int = 200,
        *,
        trigger: SeverityLike = Severity.ERROR,
        capture_level: SeverityLike = Severity.DEBUG,
    ) -> None:
        super().__init__(int(Severity.coerce(capture_level)))
        self.target = target
        self.capacity = int(capacity)
        self.trigger = int(Severity.coerce(trigger))
        self.flushes = 0
        self._buffer: Deque[logging.LogRecord] = collections.deque(
            maxlen=self.capacity
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Keep the record or send it to the target handler."""
        try:
            if record.levelno < self.target.level:
                self._buffer.append(record)
                return
            if record.levelno >= self.trigger and self._buffer:
                self._write_buffer(record)
            self.target.handle(record)
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def _write_buffer(self, cause: logging.LogRecord) -> None:
        kept = list(self._buffer)
        self._buffer.clear()
        self.flushes += 1
        definition = lookup("ANN-I-0340")
        values = {
            "count": len(kept),
            "trigger": Severity.coerce(cause.levelno).name,
        }
        marker = logging.LogRecord(
            "annunciator.recorder", int(Severity.INFO), cause.pathname,
            cause.lineno,
            definition.format(**values) if definition else "Flight recorder",
            None, None, cause.funcName,
        )
        marker.created = kept[0].created
        marker.ann_code = "ANN-I-0340"
        marker.ann_fields = values
        marker.ann_context = {}
        marker.ann_cause = definition.cause if definition else ""
        marker.ann_remedy = definition.remedy if definition else ""
        self.target.handle(marker)
        for item in kept:
            fields = dict(getattr(item, "ann_fields", None) or {})
            fields["flight_recorder"] = True
            item.ann_fields = fields
            self.target.handle(item)

    def discard(self) -> int:
        """Remove the kept records without writing them.

        Returns
        -------
        int
            The number of records that the method removed.
        """
        count = len(self._buffer)
        self._buffer.clear()
        return count

    def flush(self) -> None:
        """Flush the target handler. The kept records stay in memory."""
        self.target.flush()

    def close(self) -> None:
        """Close the target handler and remove the kept records."""
        self._buffer.clear()
        try:
            self.target.close()
        finally:
            super().close()
