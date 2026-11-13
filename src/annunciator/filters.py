"""Filters.

A filter accepts, rejects or changes a log record before a handler
writes it. Add a filter to a handler with ``handler.addFilter``. The
:func:`~annunciator.config.configure` function adds the filters that the
configuration selects.

Examples
--------
>>> import logging
>>> from annunciator.filters import RedactionFilter
>>> record = logging.LogRecord("demo", 20, __file__, 1, "login", (), None)
>>> record.ann_fields = {"user": "tom", "api_token": "abc123"}
>>> RedactionFilter().filter(record)
True
>>> record.ann_fields
{'user': 'tom', 'api_token': '[REDACTED]'}
"""

from __future__ import annotations

import fnmatch
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, Iterable, Optional, Pattern, Sequence, Tuple, Union

from .context import get_context
from .levels import Severity, SeverityLike

__all__ = [
    "DEFAULT_REDACT_KEYS",
    "ContextFilter",
    "SeverityRangeFilter",
    "CodeFilter",
    "RedactionFilter",
    "DuplicateFilter",
    "RateLimitFilter",
    "LocalsFilter",
]

#: Parts of field names that identify secret data.
DEFAULT_REDACT_KEYS: Tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
)


def _decision(record: logging.LogRecord, owner: object) -> Dict[int, bool]:
    """Return the store of filter decisions of a record.

    A filter with state must give the same answer when two handlers send
    the same record to it.
    """
    store = record.__dict__.setdefault("_ann_decisions", {})
    return store


class ContextFilter(logging.Filter):
    """Filter that adds the context data to each record.

    The filter makes sure that records from standard loggers also have
    the context data. It accepts all records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add the context data and return ``True``."""
        if getattr(record, "ann_context", None) is None:
            record.ann_context = get_context()
        return True


class SeverityRangeFilter(logging.Filter):
    """Filter that accepts records in a range of severities.

    Parameters
    ----------
    minimum
        The lowest severity that the filter accepts.
    maximum
        The highest severity that the filter accepts.
    """

    def __init__(
        self,
        minimum: SeverityLike = Severity.TRACE,
        maximum: SeverityLike = Severity.CRITICAL,
    ) -> None:
        super().__init__()
        self.minimum = int(Severity.coerce(minimum))
        self.maximum = int(Severity.coerce(maximum))

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``True`` if the severity is in the range."""
        return self.minimum <= record.levelno <= self.maximum


class CodeFilter(logging.Filter):
    """Filter that accepts or rejects records by their message code.

    Parameters
    ----------
    include
        Patterns of the codes to accept, for example ``APP-E-*``. If the
        sequence is empty, the filter accepts all codes.
    exclude
        Patterns of the codes to reject.
    pass_uncoded
        If ``True``, accept records that have no message code.

    Notes
    -----
    The patterns use the syntax of the :mod:`fnmatch` module.
    """

    def __init__(
        self,
        include: Sequence[str] = (),
        exclude: Sequence[str] = (),
        *,
        pass_uncoded: bool = True,
    ) -> None:
        super().__init__()
        self.include = tuple(include)
        self.exclude = tuple(exclude)
        self.pass_uncoded = pass_uncoded

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``True`` if the filter accepts the code of the record."""
        code = getattr(record, "ann_code", None)
        if not code:
            return self.pass_uncoded
        if any(fnmatch.fnmatchcase(code, item) for item in self.exclude):
            return False
        if not self.include:
            return True
        return any(fnmatch.fnmatchcase(code, item) for item in self.include)


class RedactionFilter(logging.Filter):
    """Filter that removes secret data from records.

    The filter replaces the value of each field that has a secret name.
    It also replaces each part of the message text that agrees with a
    pattern. The filter accepts all records.

    Parameters
    ----------
    keys
        Parts of field names. If a field name contains one of these
        parts, the filter replaces the value. Letter case is not
        important.
    patterns
        Regular expressions for secret text in messages and in text
        values.
    mask
        The text that replaces the secret data.
    """

    def __init__(
        self,
        keys: Iterable[str] = DEFAULT_REDACT_KEYS,
        patterns: Iterable[Union[str, Pattern[str]]] = (),
        mask: str = "[REDACTED]",
    ) -> None:
        super().__init__()
        self.keys = tuple(key.lower() for key in keys)
        self.patterns = tuple(
            re.compile(item) if isinstance(item, str) else item
            for item in patterns
        )
        self.mask = mask

    def _scrub_text(self, text: str) -> str:
        for pattern in self.patterns:
            text = pattern.sub(self.mask, text)
        return text

    def _scrub(self, value: Any, key: str = "") -> Any:
        lowered = key.lower()
        if lowered and any(part in lowered for part in self.keys):
            return self.mask
        if isinstance(value, dict):
            return {k: self._scrub(v, str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._scrub(item) for item in value)
        if isinstance(value, str) and self.patterns:
            return self._scrub_text(value)
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        """Remove the secret data and return ``True``."""
        for name in ("ann_fields", "ann_context", "ann_locals"):
            data = getattr(record, name, None)
            if data:
                setattr(record, name, self._scrub(data))
        if self.patterns:
            try:
                message = record.getMessage()
            except Exception:  # noqa: BLE001
                message = str(record.msg)
            cleaned = self._scrub_text(message)
            if cleaned != message:
                record.msg = cleaned
                record.args = ()
        return True


class DuplicateFilter(logging.Filter):
    """Filter that rejects equal records in a time window.

    Two records are equal if they have the same logger, severity, code
    and message text. When the filter accepts a record again after the
    window, it adds the field ``repeats`` with the number of rejected
    records.

    Parameters
    ----------
    window
        The length of the time window in seconds.
    max_entries
        The maximum number of different records that the filter keeps
        in memory.
    exempt_from
        The filter always accepts records of this severity or higher.
        Give ``None`` to apply the filter to all records.
    clock
        A function that returns the time in seconds. The default is
        :func:`time.monotonic`.
    """

    def __init__(
        self,
        window: float = 5.0,
        *,
        max_entries: int = 1024,
        exempt_from: Optional[SeverityLike] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self.window = float(window)
        self.max_entries = int(max_entries)
        self.exempt_from = (
            None if exempt_from is None else int(Severity.coerce(exempt_from))
        )
        self._clock = clock
        self._seen: Dict[Tuple[Any, ...], Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``False`` for an equal record in the time window."""
        if self.exempt_from is not None and record.levelno >= self.exempt_from:
            return True
        decisions = _decision(record, self)
        if id(self) in decisions:
            return decisions[id(self)]
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            message = str(record.msg)
        key = (record.name, record.levelno, getattr(record, "ann_code", None), message)
        now = self._clock()
        with self._lock:
            last, repeats = self._seen.get(key, (None, 0))
            if last is not None and now - last < self.window:
                self._seen[key] = (last, repeats + 1)
                accepted = False
            else:
                if repeats:
                    fields = dict(getattr(record, "ann_fields", None) or {})
                    fields["repeats"] = repeats
                    record.ann_fields = fields
                if len(self._seen) >= self.max_entries:
                    oldest = min(self._seen, key=lambda item: self._seen[item][0])
                    del self._seen[oldest]
                self._seen[key] = (now, 0)
                accepted = True
        decisions[id(self)] = accepted
        return accepted


class RateLimitFilter(logging.Filter):
    """Filter that limits the number of records in a unit of time.

    The filter uses a token bucket. Each accepted record uses one token.
    The bucket gets ``rate`` new tokens each second, to a maximum of
    ``burst`` tokens.

    Parameters
    ----------
    rate
        The mean number of records that the filter accepts each second.
    burst
        The maximum number of records that the filter accepts at one
        time.
    exempt_from
        The filter always accepts records of this severity or higher.
    clock
        A function that returns the time in seconds.

    Attributes
    ----------
    dropped : int
        The number of records that the filter rejected.
    """

    def __init__(
        self,
        rate: float = 50.0,
        burst: int = 100,
        *,
        exempt_from: Optional[SeverityLike] = Severity.ERROR,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        if rate <= 0 or burst < 1:
            raise ValueError("rate must be more than 0 and burst must be 1 or more")
        self.rate = float(rate)
        self.burst = int(burst)
        self.exempt_from = (
            None if exempt_from is None else int(Severity.coerce(exempt_from))
        )
        self.dropped = 0
        self._clock = clock
        self._tokens = float(burst)
        self._last = clock()
        self._lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``False`` if no token is available."""
        if self.exempt_from is not None and record.levelno >= self.exempt_from:
            return True
        decisions = _decision(record, self)
        if id(self) in decisions:
            return decisions[id(self)]
        with self._lock:
            now = self._clock()
            self._tokens = min(
                float(self.burst), self._tokens + (now - self._last) * self.rate
            )
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                accepted = True
            else:
                self.dropped += 1
                accepted = False
        decisions[id(self)] = accepted
        return accepted


class LocalsFilter(logging.Filter):
    """Filter that adds the local variables of a failure to a record.

    When a record has an exception, the filter reads the local variables
    of the last frames of the traceback. It keeps a short text for each
    value. The redaction filter then removes secret data. The filter
    accepts all records.

    Parameters
    ----------
    depth
        The number of frames to read. The last frame is the function
        that raised the exception.
    max_length
        The maximum number of characters for each value.
    max_items
        The maximum number of variables for each frame.
    """

    def __init__(
        self, depth: int = 2, *, max_length: int = 200, max_items: int = 40
    ) -> None:
        super().__init__()
        self.depth = int(depth)
        self.max_length = int(max_length)
        self.max_items = int(max_items)

    def _text(self, value: Any) -> str:
        try:
            text = repr(value)
        except Exception:  # noqa: BLE001 - a repr method that fails
            text = f"<{type(value).__name__}: no text available>"
        if len(text) > self.max_length:
            text = text[: self.max_length - 3] + "..."
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """Add the local variables and return ``True``."""
        if getattr(record, "ann_locals", None) is not None:
            return True
        info = record.exc_info
        if not info or info[2] is None:
            return True
        frames = []
        tb = info[2]
        while tb is not None:
            frames.append(tb)
            tb = tb.tb_next
        captured: Dict[str, Dict[str, str]] = {}
        for item in frames[-self.depth:]:
            code = item.tb_frame.f_code
            label = (
                f"{code.co_name} "
                f"({code.co_filename.replace(chr(92), '/').rsplit('/', 1)[-1]}:"
                f"{item.tb_lineno})"
            )
            values: Dict[str, str] = {}
            for name, value in item.tb_frame.f_locals.items():
                if name.startswith("__") or len(values) >= self.max_items:
                    continue
                kind = type(value).__name__
                if kind in ("module", "function", "type", "builtin_function_or_method"):
                    continue
                values[name] = self._text(value)
            captured[label] = values
        record.ann_locals = captured
        return True
