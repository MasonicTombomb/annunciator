"""Tools for tests.

Use this module to examine the events that your code records.

* :func:`capture_events` is a context manager for all test tools.
* ``annunciator_events`` is a fixture for pytest. The library registers
  it automatically when pytest is installed.

Examples
--------
>>> from annunciator import get_logger
>>> from annunciator.testing import capture_events
>>> with capture_events() as captured:
...     get_logger("demo").warning("Low count rate", rate=1.5)
>>> event = captured.assert_logged(severity="WARNING", text="count rate")
>>> event.fields["rate"]
1.5
>>> captured.assert_not_logged(minimum="ERROR")
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Iterator, List, Optional

from .events import Event
from .levels import Severity, SeverityLike
from .logger import reset_occurrences

__all__ = ["EventCapture", "capture_events"]


class EventCapture(logging.Handler):
    """Handler that collects events for a test.

    Attributes
    ----------
    events : list of Event
        The collected events, oldest first.
    """

    def __init__(self, level: SeverityLike = Severity.TRACE) -> None:
        super().__init__(int(Severity.coerce(level)))
        self.events: List[Event] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Add the event of a record."""
        self.events.append(Event.from_record(record))

    @property
    def codes(self) -> List[str]:
        """The message codes of the events that have a code."""
        return [event.code for event in self.events if event.code]

    @property
    def messages(self) -> List[str]:
        """The message texts of the events."""
        return [event.message for event in self.events]

    def clear(self) -> None:
        """Remove all collected events."""
        self.events.clear()

    def select(
        self,
        code: Optional[str] = None,
        *,
        severity: Optional[SeverityLike] = None,
        minimum: Optional[SeverityLike] = None,
        text: Optional[str] = None,
        logger: Optional[str] = None,
        **fields: Any,
    ) -> List[Event]:
        """Return the events that agree with all given conditions.

        Parameters
        ----------
        code
            The message code.
        severity
            The severity.
        minimum
            The lowest severity.
        text
            A text that the message must contain.
        logger
            The name of the logger.
        **fields
            Structured fields and their values.
        """
        result = []
        for event in self.events:
            if code is not None and event.code != code:
                continue
            if severity is not None and event.severity != Severity.coerce(severity):
                continue
            if minimum is not None and event.severity < Severity.coerce(minimum):
                continue
            if text is not None and text not in event.message:
                continue
            if logger is not None and event.logger != logger:
                continue
            if any(event.fields.get(k, _MISSING) != v for k, v in fields.items()):
                continue
            result.append(event)
        return result

    def _describe(self) -> str:
        if not self.events:
            return "No events were recorded."
        rows = [
            f"  {event.severity.name:<8} {event.code or '-':<14} {event.message}"
            for event in self.events[-20:]
        ]
        return "Recorded events (last 20):\n" + "\n".join(rows)

    def assert_logged(
        self,
        code: Optional[str] = None,
        *,
        count: Optional[int] = None,
        **conditions: Any,
    ) -> Event:
        """Make sure that an event was recorded.

        Parameters
        ----------
        code
            The message code.
        count
            The necessary number of events. ``None`` accepts one or
            more events.
        **conditions
            The other conditions of :meth:`select`.

        Returns
        -------
        Event
            The first event that agrees with the conditions.

        Raises
        ------
        AssertionError
            If the number of events is not correct.
        """
        found = self.select(code, **conditions)
        wanted = {"code": code, **conditions}
        if count is None and not found:
            raise AssertionError(
                f"No event agrees with {wanted}.\n{self._describe()}"
            )
        if count is not None and len(found) != count:
            raise AssertionError(
                f"{len(found)} events agree with {wanted}; the necessary "
                f"number is {count}.\n{self._describe()}"
            )
        return found[0] if found else None  # type: ignore[return-value]

    def assert_not_logged(self, code: Optional[str] = None, **conditions: Any) -> None:
        """Make sure that no event agrees with the conditions.

        Raises
        ------
        AssertionError
            If one or more events agree with the conditions.
        """
        found = self.select(code, **conditions)
        if found:
            wanted = {"code": code, **conditions}
            raise AssertionError(
                f"{len(found)} events agree with {wanted}.\n{self._describe()}"
            )

    def assert_no_problems(self, minimum: SeverityLike = Severity.WARNING) -> None:
        """Make sure that no event has the given severity or higher.

        Raises
        ------
        AssertionError
            If one or more events have the severity or higher.
        """
        self.assert_not_logged(minimum=minimum)


_MISSING = object()


@contextlib.contextmanager
def capture_events(
    logger: str = "", level: SeverityLike = Severity.TRACE
) -> Iterator[EventCapture]:
    """Collect the events of a block of code.

    Parameters
    ----------
    logger
        The name of the logger to examine. The empty text selects the
        root logger and thus all loggers.
    level
        The minimum severity to collect. The function decreases the
        level of the logger for the duration of the block, if this is
        necessary.

    Yields
    ------
    EventCapture
        The object that contains the events.
    """
    target = logging.getLogger(logger or None)
    capture = EventCapture(level)
    previous = target.level
    wanted = int(Severity.coerce(level))
    if previous == logging.NOTSET or previous > wanted:
        target.setLevel(wanted)
    target.addHandler(capture)
    try:
        yield capture
    finally:
        target.removeHandler(capture)
        target.setLevel(previous)


try:  # pragma: no cover - only with pytest
    import pytest
except ImportError:  # pragma: no cover
    pytest = None  # type: ignore[assignment]

if pytest is not None:  # pragma: no cover

    @pytest.fixture
    def annunciator_events() -> Iterator[EventCapture]:
        """Fixture that collects all events of one test.

        The fixture also sets the state of the methods ``once``,
        ``every`` and ``throttle`` to its initial condition.
        """
        reset_occurrences()
        with capture_events() as capture:
            yield capture
