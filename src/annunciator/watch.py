"""Progress records and stall detection.

Long operations must show that they are in operation. This module has
two tools:

* :class:`Progress` records the state of an operation at a controlled
  interval, with the rate and the time to completion.
* :class:`Watchdog` records a warning when an operation does not report
  progress in a permitted time.

Examples
--------
>>> from annunciator.watch import track
>>> total = 0
>>> for value in track(range(5), "sum", interval=3600):
...     total += value
>>> total
10
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar

from .handling import LoggerLike, _resolve_logger
from .levels import Severity, SeverityLike

__all__ = ["Progress", "Watchdog", "track"]

T = TypeVar("T")


class Watchdog:
    """Object that finds an operation that does not make progress.

    A thread in the background examines the time of the last call of
    :meth:`beat`. If the time is more than the limit, the watchdog
    records the code ``ANN-W-0332``. When the operation continues, the
    watchdog records the code ``ANN-I-0333``.

    Parameters
    ----------
    timeout
        The permitted time in seconds between two calls of
        :meth:`beat`.
    operation
        The name of the operation for the records.
    logger
        A structured logger, a standard logger or a logger name.
    on_stall
        A function that the watchdog calls when it finds a stall. The
        function gets the idle time in seconds.
    repeat
        If ``True``, record the warning again after each subsequent
        ``timeout`` interval of the same stall.

    Attributes
    ----------
    stalls : int
        The number of stalls that the watchdog found.

    Examples
    --------
    >>> from annunciator.watch import Watchdog
    >>> with Watchdog(60.0, "acquisition") as watchdog:
    ...     watchdog.beat()
    >>> watchdog.stalls
    0
    """

    def __init__(
        self,
        timeout: float,
        operation: str = "operation",
        *,
        logger: LoggerLike = None,
        on_stall: Optional[Callable[[float], Any]] = None,
        repeat: bool = True,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be more than 0")
        self.timeout = float(timeout)
        self.operation = operation
        self.stalls = 0
        self._log = _resolve_logger(logger)
        self._on_stall = on_stall
        self._repeat = repeat
        self._last = time.monotonic()
        self._reported = 0.0
        self._stalled = False
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> "Watchdog":
        """Start the thread of the watchdog."""
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._last = time.monotonic()
            self._thread = threading.Thread(
                target=self._run,
                name=f"annunciator-watchdog-{self.operation}",
                daemon=True,
            )
            self._thread.start()
        return self

    def stop(self) -> None:
        """Stop the thread of the watchdog."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def beat(self) -> None:
        """Tell the watchdog that the operation made progress."""
        with self._lock:
            now = time.monotonic()
            idle = now - self._last
            self._last = now
            was_stalled, self._stalled = self._stalled, False
        if was_stalled:
            self._log.event(
                "ANN-I-0333", operation=self.operation, idle=f"{idle:.1f}"
            )

    def _run(self) -> None:
        step = min(self.timeout / 4.0, 1.0)
        while not self._stop.wait(step):
            with self._lock:
                now = time.monotonic()
                idle = now - self._last
                if idle < self.timeout:
                    continue
                if self._stalled and (
                    not self._repeat or now - self._reported < self.timeout
                ):
                    continue
                first = not self._stalled
                self._stalled = True
                self._reported = now
            if first:
                self.stalls += 1
            self._log.event(
                "ANN-W-0332", operation=self.operation, idle=f"{idle:.1f}"
            )
            if self._on_stall is not None:
                try:
                    self._on_stall(idle)
                except Exception as exc:  # noqa: BLE001
                    self._log.report(exc, operation="watchdog on_stall")

    def __enter__(self) -> "Watchdog":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop()
        return False


class Progress:
    """Object that records the progress of a long operation.

    The object records the code ``ANN-I-0330`` a maximum of one time in
    each interval. At the end, it records the code ``ANN-I-0331``.

    Parameters
    ----------
    operation
        The name of the operation for the records.
    total
        The number of items, or ``None`` if the number is not known.
    interval
        The minimum time in seconds between two progress records.
    logger
        A structured logger, a standard logger or a logger name.
    severity
        The severity of the progress records.
    stall_after
        A time in seconds. If you give a value, the object starts a
        :class:`Watchdog` with this limit.
    **fields
        More structured fields for the records.

    Attributes
    ----------
    done : int
        The number of completed items.

    Examples
    --------
    >>> from annunciator.watch import Progress
    >>> with Progress("fit spectra", total=3, interval=3600) as progress:
    ...     for _ in range(3):
    ...         progress.update()
    >>> progress.done
    3
    """

    def __init__(
        self,
        operation: str,
        total: Optional[int] = None,
        *,
        interval: float = 10.0,
        logger: LoggerLike = None,
        severity: SeverityLike = Severity.INFO,
        stall_after: Optional[float] = None,
        **fields: Any,
    ) -> None:
        self.operation = operation
        self.total = total
        self.interval = float(interval)
        self.done = 0
        self._log = _resolve_logger(logger)
        self._severity = Severity.coerce(severity)
        self._fields = fields
        self._start = time.monotonic()
        self._last_record = self._start
        self._closed = False
        self.watchdog: Optional[Watchdog] = None
        if stall_after is not None:
            self.watchdog = Watchdog(stall_after, operation, logger=self._log)

    @property
    def elapsed(self) -> float:
        """The time in seconds from the start of the operation."""
        return time.monotonic() - self._start

    def update(self, count: int = 1) -> None:
        """Add completed items and record the progress if the interval is over.

        Parameters
        ----------
        count
            The number of items that the operation completed.
        """
        self.done += count
        if self.watchdog is not None:
            self.watchdog.beat()
        now = time.monotonic()
        if now - self._last_record >= self.interval:
            self._last_record = now
            self._record()

    def _record(self) -> None:
        elapsed = max(self.elapsed, 1e-9)
        rate = self.done / elapsed
        if self.total:
            percent = f"{100.0 * self.done / self.total:.1f}"
            remaining = max(self.total - self.done, 0)
            eta = f"{remaining / rate:.0f}" if rate > 0 else "not known"
            total = str(self.total)
        else:
            percent = eta = total = "not known"
        values = {
            "operation": self.operation,
            "done": self.done,
            "total": total,
            "percent": percent,
            "rate": f"{rate:.3g}",
            "eta": eta,
        }
        values.update(self._fields)
        from .catalogue import lookup

        definition = lookup("ANN-I-0330")
        self._log.log(
            self._severity,
            definition.format(**values) if definition else "Progress",
            code="ANN-I-0330",
            stacklevel=3,
            **values,
        )

    def close(self) -> None:
        """Record the end of the operation and stop the watchdog."""
        if self._closed:
            return
        self._closed = True
        if self.watchdog is not None:
            self.watchdog.stop()
        self._log.event(
            "ANN-I-0331",
            stacklevel=3,
            operation=self.operation,
            done=self.done,
            elapsed=f"{self.elapsed:.3f}",
            **self._fields,
        )

    def __enter__(self) -> "Progress":
        self._start = time.monotonic()
        self._last_record = self._start
        if self.watchdog is not None:
            self.watchdog.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self.close()
        elif self.watchdog is not None:
            self.watchdog.stop()
        return False


def track(
    iterable: Iterable[T],
    operation: str,
    *,
    total: Optional[int] = None,
    interval: float = 10.0,
    logger: LoggerLike = None,
    stall_after: Optional[float] = None,
    **fields: Any,
) -> Iterator[T]:
    """Give the items of an iterable and record the progress.

    Parameters
    ----------
    iterable
        The items of the operation.
    operation
        The name of the operation for the records.
    total
        The number of items. The default is ``len(iterable)``, if the
        length is available.
    interval
        The minimum time in seconds between two progress records.
    logger
        A structured logger, a standard logger or a logger name.
    stall_after
        A time in seconds for the stall detection, or ``None``.
    **fields
        More structured fields for the records.

    Yields
    ------
    object
        The items of the iterable.
    """
    if total is None:
        try:
            total = len(iterable)  # type: ignore[arg-type]
        except TypeError:
            total = None
    with Progress(
        operation, total, interval=interval, logger=logger,
        stall_after=stall_after, **fields,
    ) as progress:
        for item in iterable:
            yield item
            progress.update()
