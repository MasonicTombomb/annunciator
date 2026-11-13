"""Reports.

The functions of this module read, select, write and summarise events.
The source of the events can be the event store or a JSON Lines log
file.

Examples
--------
>>> from annunciator import Event, Severity
>>> from annunciator.report import EventReport
>>> events = [
...     Event(severity=Severity.INFO, message="Start"),
...     Event(severity=Severity.ERROR, message="No beam", code="APP-E-0001"),
... ]
>>> report = EventReport.from_events(events)
>>> report.total, report.worst.name, report.exit_code()
(2, 'ERROR', 1)
"""

from __future__ import annotations

import csv
import datetime as _dt
import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

from .errors import DataError
from .events import Event, json_default
from .levels import Severity, SeverityLike

__all__ = [
    "EventReport",
    "read_events",
    "write_events",
    "export_csv",
    "select_events",
    "summarise",
    "RunComparison",
    "compare_runs",
]


@dataclass
class EventReport:
    """Summary of a set of events.

    Attributes
    ----------
    total : int
        The number of events.
    by_severity : dict
        The number of events for each severity name.
    by_code : dict
        The number of events for each message code.
    by_logger : dict
        The number of events for each logger name.
    first : datetime or None
        The time of the first event.
    last : datetime or None
        The time of the last event.
    worst : Severity or None
        The highest severity in the set.
    by_fingerprint : dict
        The distinct failures. The keys are fingerprints. Each value is
        a dictionary with the keys ``count``, ``type``, ``message``,
        ``first`` and ``last``.
    """

    total: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_code: Dict[str, int] = field(default_factory=dict)
    by_logger: Dict[str, int] = field(default_factory=dict)
    first: Optional[_dt.datetime] = None
    last: Optional[_dt.datetime] = None
    worst: Optional[Severity] = None
    by_fingerprint: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_events(cls, events: Iterable[Event]) -> "EventReport":
        """Make a report from events."""
        report = cls()
        for event in events:
            report.total += 1
            name = event.severity.name
            report.by_severity[name] = report.by_severity.get(name, 0) + 1
            if event.code:
                report.by_code[event.code] = report.by_code.get(event.code, 0) + 1
            if event.logger:
                report.by_logger[event.logger] = (
                    report.by_logger.get(event.logger, 0) + 1
                )
            if report.first is None or event.timestamp < report.first:
                report.first = event.timestamp
            if report.last is None or event.timestamp > report.last:
                report.last = event.timestamp
            if report.worst is None or event.severity > report.worst:
                report.worst = event.severity
            exc = event.exception
            if exc is not None and exc.fingerprint:
                item = report.by_fingerprint.setdefault(
                    exc.fingerprint,
                    {
                        "count": 0,
                        "type": exc.type,
                        "message": exc.message,
                        "first": event.timestamp,
                        "last": event.timestamp,
                    },
                )
                item["count"] += 1
                item["first"] = min(item["first"], event.timestamp)
                item["last"] = max(item["last"], event.timestamp)
        return report

    def count(self, minimum: SeverityLike) -> int:
        """Return the number of events of a severity or higher."""
        floor = Severity.coerce(minimum)
        return sum(
            number
            for name, number in self.by_severity.items()
            if Severity[name] >= floor
        )

    @property
    def has_warnings(self) -> bool:
        """``True`` if the set contains ``WARNING`` or higher."""
        return self.worst is not None and self.worst >= Severity.WARNING

    @property
    def has_errors(self) -> bool:
        """``True`` if the set contains ``ERROR`` or higher."""
        return self.worst is not None and self.worst >= Severity.ERROR

    def exit_code(self) -> int:
        """Return an exit status for a command-line program.

        Returns
        -------
        int
            0 if the set has no errors, 1 if the worst severity is
            ``ERROR``, 2 if the worst severity is ``CRITICAL``.
        """
        if self.worst is None or self.worst < Severity.ERROR:
            return 0
        return 2 if self.worst >= Severity.CRITICAL else 1

    def to_dict(self) -> Dict[str, Any]:
        """Return the report as a dictionary that JSON can contain."""
        return {
            "total": self.total,
            "worst": self.worst.name if self.worst else None,
            "first": self.first.isoformat() if self.first else None,
            "last": self.last.isoformat() if self.last else None,
            "by_severity": dict(self.by_severity),
            "by_code": dict(self.by_code),
            "by_logger": dict(self.by_logger),
            "by_fingerprint": {
                key: {
                    "count": item["count"],
                    "type": item["type"],
                    "message": item["message"],
                    "first": item["first"].isoformat(),
                    "last": item["last"].isoformat(),
                }
                for key, item in self.by_fingerprint.items()
            },
        }

    def to_text(self) -> str:
        """Return the report as readable text."""
        lines = [f"Events: {self.total}"]
        if self.total == 0:
            return lines[0]
        lines.append(f"Worst severity: {self.worst.name if self.worst else '-'}")
        if self.first and self.last:
            lines.append(f"First event: {self.first.isoformat(timespec='seconds')}")
            lines.append(f"Last event:  {self.last.isoformat(timespec='seconds')}")
        lines.append("By severity:")
        for member in sorted(Severity, reverse=True):
            number = self.by_severity.get(member.name)
            if number:
                lines.append(f"  {member.name:<8} {number}")
        if self.by_code:
            lines.append("By message code:")
            ordered = sorted(self.by_code.items(), key=lambda item: (-item[1], item[0]))
            for code, number in ordered:
                lines.append(f"  {code:<16} {number}")
        if self.by_fingerprint:
            lines.append(f"Distinct failures: {len(self.by_fingerprint)}")
            failures = sorted(
                self.by_fingerprint.items(), key=lambda item: -item[1]["count"]
            )
            for key, item in failures:
                text = str(item["message"]).splitlines()[0] if item["message"] else ""
                if len(text) > 70:
                    text = text[:67] + "..."
                lines.append(
                    f"  {key}  {item['count']:>5} x  {item['type']}: {text}"
                )
        return "\n".join(lines)


def read_events(path: Union[str, Path], *, strict: bool = True) -> Iterator[Event]:
    """Read the events of a JSON Lines log file.

    Parameters
    ----------
    path
        The path of the file.
    strict
        If ``True``, raise an exception for an incorrect line. If
        ``False``, ignore incorrect lines.

    Yields
    ------
    Event
        The events of the file, in the sequence of the lines.

    Raises
    ------
    DataError
        If ``strict`` is ``True`` and a line is not a correct event
        record (``ANN-E-0501``).
    """
    file = Path(path)
    with file.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                yield Event.from_json(line)
            except (ValueError, TypeError, KeyError) as exc:
                if strict:
                    raise DataError(
                        code="ANN-E-0501", line=number, path=str(file)
                    ) from exc


def write_events(events: Iterable[Event], path: Union[str, Path]) -> int:
    """Write events to a JSON Lines file.

    Returns
    -------
    int
        The number of events that the function wrote.
    """
    count = 0
    with Path(path).open("w", encoding="utf-8") as stream:
        for event in events:
            stream.write(event.to_json() + "\n")
            count += 1
    return count


_CSV_COLUMNS = (
    "timestamp", "severity", "code", "logger", "message", "cause", "remedy",
    "exception_type", "exception_message", "fields",
)


def export_csv(events: Iterable[Event], path: Union[str, Path]) -> int:
    """Write events to a CSV file.

    The file has one row for each event. The column ``fields`` contains
    the structured fields as JSON text.

    Returns
    -------
    int
        The number of events that the function wrote.
    """
    count = 0
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_CSV_COLUMNS)
        for event in events:
            data = event.to_dict()
            exc = data.get("exception", {})
            writer.writerow(
                [
                    data.get("timestamp", ""),
                    data.get("severity", ""),
                    data.get("code", ""),
                    data.get("logger", ""),
                    data.get("message", ""),
                    data.get("cause", ""),
                    data.get("remedy", ""),
                    exc.get("type", ""),
                    exc.get("message", ""),
                    json.dumps(data.get("fields", {}), default=json_default),
                ]
            )
            count += 1
    return count


def select_events(
    events: Iterable[Event],
    *,
    minimum: Optional[SeverityLike] = None,
    maximum: Optional[SeverityLike] = None,
    code: Optional[str] = None,
    logger: Optional[str] = None,
    text: Optional[str] = None,
    fingerprint: Optional[str] = None,
    since: Optional[_dt.datetime] = None,
    until: Optional[_dt.datetime] = None,
) -> Iterator[Event]:
    """Select the events that agree with all given conditions.

    Parameters
    ----------
    events
        The events to examine.
    minimum
        Keep only the events of this severity or higher.
    maximum
        Keep only the events of this severity or lower.
    code
        A pattern for the message code, for example ``APP-E-*``.
    logger
        A pattern for the logger name.
    text
        Keep only the events that contain this text in the message.
        Letter case is not important.
    fingerprint
        Keep only the events with an exception that has this
        fingerprint.
    since
        Keep only the events at or after this time.
    until
        Keep only the events at or before this time.

    Notes
    -----
    The patterns use the syntax of the :mod:`fnmatch` module.
    """
    floor = None if minimum is None else Severity.coerce(minimum)
    ceiling = None if maximum is None else Severity.coerce(maximum)
    needle = text.lower() if text else None
    for event in events:
        if floor is not None and event.severity < floor:
            continue
        if ceiling is not None and event.severity > ceiling:
            continue
        if code is not None and not fnmatch.fnmatchcase(event.code or "", code):
            continue
        if logger is not None and not fnmatch.fnmatchcase(event.logger, logger):
            continue
        if needle is not None and needle not in event.message.lower():
            continue
        if fingerprint is not None and (
            event.exception is None or event.exception.fingerprint != fingerprint
        ):
            continue
        if since is not None and event.timestamp < since:
            continue
        if until is not None and event.timestamp > until:
            continue
        yield event


def summarise(
    source: Union[str, Path, Iterable[Event], None] = None
) -> EventReport:
    """Make a report from a log file, from events or from the event store.

    Parameters
    ----------
    source
        The path of a JSON Lines log file, or events. ``None`` selects
        the event store of the configuration.

    Returns
    -------
    EventReport
        The report. If the event store is not available, the report is
        empty.
    """
    if source is None:
        from .config import get_store

        store = get_store()
        return EventReport.from_events(store.events if store is not None else [])
    if isinstance(source, (str, Path)):
        return EventReport.from_events(read_events(source, strict=False))
    return EventReport.from_events(source)


@dataclass
class RunComparison:
    """The differences between the events of two runs.

    Attributes
    ----------
    new_codes : dict
        The message codes that occur only in the second run, with their
        counts.
    gone_codes : dict
        The message codes that occur only in the first run, with their
        counts.
    changed_codes : dict
        The message codes that have different counts. Each value is a
        tuple of the first count and the second count.
    severity_changes : dict
        The severities that have different counts. Each value is a
        tuple of the first count and the second count.
    new_failures : dict
        The failures that occur only in the second run. The keys are
        fingerprints. The values are texts.
    gone_failures : dict
        The failures that occur only in the first run.
    """

    new_codes: Dict[str, int] = field(default_factory=dict)
    gone_codes: Dict[str, int] = field(default_factory=dict)
    changed_codes: Dict[str, tuple] = field(default_factory=dict)
    severity_changes: Dict[str, tuple] = field(default_factory=dict)
    new_failures: Dict[str, str] = field(default_factory=dict)
    gone_failures: Dict[str, str] = field(default_factory=dict)

    @property
    def regression(self) -> bool:
        """``True`` if the second run has new problems.

        A new problem is a new failure or a new message code of the
        severity ``WARNING`` or higher.
        """
        if self.new_failures:
            return True
        return any(_code_letter(code) in "WEC" for code in self.new_codes)

    @property
    def identical(self) -> bool:
        """``True`` if the comparison found no differences."""
        return not (
            self.new_codes or self.gone_codes or self.changed_codes
            or self.severity_changes or self.new_failures or self.gone_failures
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the comparison as a dictionary that JSON can contain."""
        return {
            "regression": self.regression,
            "new_codes": dict(self.new_codes),
            "gone_codes": dict(self.gone_codes),
            "changed_codes": {k: list(v) for k, v in self.changed_codes.items()},
            "severity_changes": {
                k: list(v) for k, v in self.severity_changes.items()
            },
            "new_failures": dict(self.new_failures),
            "gone_failures": dict(self.gone_failures),
        }

    def to_text(self) -> str:
        """Return the comparison as readable text."""
        if self.identical:
            return "The two runs have the same message counts."
        lines: List[str] = []

        def section(title: str, rows: List[str]) -> None:
            if rows:
                lines.append(title)
                lines.extend(f"  {row}" for row in rows)

        section(
            "Severity counts (first run -> second run):",
            [f"{k:<8} {a} -> {b}" for k, (a, b) in self.severity_changes.items()],
        )
        section(
            "New message codes in the second run:",
            [f"{k:<16} {v}" for k, v in sorted(self.new_codes.items())],
        )
        section(
            "Message codes only in the first run:",
            [f"{k:<16} {v}" for k, v in sorted(self.gone_codes.items())],
        )
        section(
            "Message codes with different counts:",
            [f"{k:<16} {a} -> {b}" for k, (a, b) in sorted(self.changed_codes.items())],
        )
        section(
            "New failures in the second run:",
            [f"{k}  {v}" for k, v in self.new_failures.items()],
        )
        section(
            "Failures only in the first run:",
            [f"{k}  {v}" for k, v in self.gone_failures.items()],
        )
        lines.append(
            "Result: the second run has new problems."
            if self.regression
            else "Result: the second run has no new problems."
        )
        return "\n".join(lines)


def _code_letter(code: str) -> str:
    parts = code.split("-")
    return parts[1] if len(parts) == 3 else ""


def compare_runs(
    first: Union[str, Path, Iterable[Event], EventReport],
    second: Union[str, Path, Iterable[Event], EventReport],
) -> RunComparison:
    """Compare the events of two runs.

    Use this function to find what changed between a good run and a
    bad run, or between two versions of a program.

    Parameters
    ----------
    first
        The reference run: the path of a JSON Lines log file, events or
        a report.
    second
        The run to examine, in one of the same forms.

    Returns
    -------
    RunComparison
        The differences.
    """
    a = first if isinstance(first, EventReport) else summarise(first)
    b = second if isinstance(second, EventReport) else summarise(second)
    result = RunComparison()
    for code in sorted(set(a.by_code) | set(b.by_code)):
        x, y = a.by_code.get(code, 0), b.by_code.get(code, 0)
        if x == 0:
            result.new_codes[code] = y
        elif y == 0:
            result.gone_codes[code] = x
        elif x != y:
            result.changed_codes[code] = (x, y)
    for member in sorted(Severity, reverse=True):
        x = a.by_severity.get(member.name, 0)
        y = b.by_severity.get(member.name, 0)
        if x != y:
            result.severity_changes[member.name] = (x, y)

    def label(item: Dict[str, Any]) -> str:
        text = str(item["message"]).splitlines()[0] if item["message"] else ""
        return f"{item['type']}: {text[:70]}"

    for key, item in b.by_fingerprint.items():
        if key not in a.by_fingerprint:
            result.new_failures[key] = label(item)
    for key, item in a.by_fingerprint.items():
        if key not in b.by_fingerprint:
            result.gone_failures[key] = label(item)
    return result
