"""Tamper-evident log files.

This module makes a JSON Lines log file with a chain. Each record
contains a hash of the record before it. The records thus make a chain. If a person
changes, removes or adds a record, the chain is broken and
:func:`verify_chain` finds the position.

Each record has the object ``chain`` with three keys:

``seq``
    The sequence number of the record. The first record has the number 1.
``prev``
    The hash of the record before this record.
``hash``
    The hash of ``prev`` and of the contents of this record.

Without a key, the hash function is SHA-256. With a key, the function is
HMAC-SHA-256. A person who does not have the key cannot make a correct
chain again after a change.

Examples
--------
>>> import logging, os, tempfile
>>> from annunciator.integrity import ChainFormatter, verify_chain
>>> path = os.path.join(tempfile.mkdtemp(), "run.jsonl")
>>> handler = logging.FileHandler(path, encoding="utf-8")
>>> handler.setFormatter(ChainFormatter())
>>> logger = logging.getLogger("doctest.integrity")
>>> logger.propagate = False
>>> logger.addHandler(handler)
>>> logger.warning("first")
>>> logger.warning("second")
>>> handler.close()
>>> result = verify_chain(path)
>>> result.ok, result.records
(True, 2)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .events import Event, json_default
from .formatters import JsonFormatter

__all__ = [
    "ChainFormatter",
    "ChainResult",
    "verify_chain",
    "chain_key_from_env",
    "GENESIS",
    "KEY_VARIABLE",
]

#: The value of ``prev`` for the first record of a chain.
GENESIS = "0" * 64
#: The environment variable that contains the key of the chain.
KEY_VARIABLE = "ANNUNCIATOR_CHAIN_KEY"


def chain_key_from_env(variable: str = KEY_VARIABLE) -> Optional[bytes]:
    """Return the key of the chain from an environment variable.

    Returns
    -------
    bytes or None
        The key, or ``None`` if the variable is not set or is empty.
    """
    value = os.environ.get(variable)
    return value.encode("utf-8") if value else None


def _canonical(data: Dict[str, Any]) -> str:
    """Return the text of a record that the hash function reads."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"),
        default=json_default, ensure_ascii=False,
    )


def _digest(previous: str, seq: int, body: str, key: Optional[bytes]) -> str:
    message = f"{previous}|{seq}|{body}".encode("utf-8")
    if key:
        return hmac.new(key, message, hashlib.sha256).hexdigest()
    return hashlib.sha256(message).hexdigest()


def _last_link(path: Path) -> Tuple[int, str]:
    """Return the sequence number and the hash of the last record of a file."""
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(size - 65536, 0))
            tail = stream.read().decode("utf-8", errors="replace")
    except OSError:
        return 0, GENESIS
    for line in reversed(tail.splitlines()):
        try:
            chain = json.loads(line).get("chain")
            return int(chain["seq"]), str(chain["hash"])
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    return 0, GENESIS


class ChainFormatter(JsonFormatter):
    """JSON formatter that adds the chain data to each record.

    Parameters
    ----------
    resume_from
        The path of the log file. If the file exists, the chain
        continues from its last record.
    key
        The key for HMAC-SHA-256, or ``None`` for SHA-256.
    include_source
        If ``True``, include the source position in each object.

    Notes
    -----
    Use one formatter for one log file. When the handler rotates the
    file, the chain continues in the new file. The first record of the
    new file then refers to the last record of the old file.
    """

    def __init__(
        self,
        resume_from: Union[str, Path, None] = None,
        *,
        key: Optional[bytes] = None,
        include_source: bool = True,
    ) -> None:
        super().__init__(include_source=include_source)
        self.key = key
        self.seq, self.last_hash = (0, GENESIS)
        if resume_from is not None and Path(resume_from).exists():
            self.seq, self.last_hash = _last_link(Path(resume_from))

    def format(self, record: logging.LogRecord) -> str:
        """Return the JSON text for a record, with the chain data."""
        # A rotating file handler formats each record two times. The chain
        # must go forward only one time for each record.
        cache = record.__dict__.setdefault("_ann_chain_lines", {})
        if id(self) in cache:
            return cache[id(self)]
        event = Event.from_record(record)
        if not self.include_source:
            event.source = None
        data = json.loads(event.to_json())
        self.seq += 1
        digest = _digest(self.last_hash, self.seq, _canonical(data), self.key)
        data["chain"] = {"seq": self.seq, "prev": self.last_hash, "hash": digest}
        self.last_hash = digest
        line = json.dumps(data, default=json_default, ensure_ascii=False)
        cache[id(self)] = line
        return line


@dataclass
class ChainResult:
    """The result of an integrity check.

    Attributes
    ----------
    path : str
        The path of the file.
    records : int
        The number of records that have correct chain data.
    first_seq : int
        The sequence number of the first record in the file. A value
        of more than 1 shows that the chain started in an older file.
    last_seq : int
        The sequence number of the last correct record.
    problems : list of tuple
        The line number and the reason for each problem.
    """

    path: str
    records: int = 0
    first_seq: int = 0
    last_seq: int = 0
    problems: List[Tuple[int, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """``True`` if the file has chain data and no problems."""
        return self.records > 0 and not self.problems

    def to_text(self) -> str:
        """Return the result as readable text."""
        if self.ok:
            lines = [
                f"The integrity check passed: {self.path}",
                f"Records: {self.records} (sequence {self.first_seq} to "
                f"{self.last_seq})",
            ]
            if self.first_seq > 1:
                lines.append(
                    "The chain started in an older file. Examine that file "
                    "also."
                )
            return "\n".join(lines)
        lines = [f"The integrity check FAILED: {self.path}"]
        if not self.records and not self.problems:
            lines.append("The file has no integrity data.")
        for number, reason in self.problems[:20]:
            lines.append(f"  line {number}: {reason}")
        if len(self.problems) > 20:
            lines.append(f"  ... and {len(self.problems) - 20} more problems")
        return "\n".join(lines)


def verify_chain(
    path: Union[str, Path],
    *,
    key: Optional[bytes] = None,
    expected_start: Optional[str] = None,
) -> ChainResult:
    """Examine the chain of a JSON Lines log file.

    Parameters
    ----------
    path
        The path of the log file.
    key
        The key that the program used when it wrote the file, or
        ``None``.
    expected_start
        The hash that the first record must refer to. Use the last hash
        of the older file to examine a file after a rotation. ``None``
        accepts all values for a file that does not start at the
        sequence number 1.

    Returns
    -------
    ChainResult
        The result of the check.

    Notes
    -----
    The check finds a changed record, a removed record, an added record
    and a changed sequence. It cannot find the removal of the last
    records of a file. To find that, keep the last hash in a different
    location and compare it.
    """
    result = ChainResult(str(path))
    previous: Optional[str] = None
    expected_seq: Optional[int] = None
    with Path(path).open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                chain = data.pop("chain")
                seq, prev, digest = int(chain["seq"]), chain["prev"], chain["hash"]
            except (ValueError, TypeError, KeyError, AttributeError):
                result.problems.append((number, "the record has no chain data"))
                continue
            if previous is None:
                result.first_seq = seq
                if seq == 1 and prev != GENESIS:
                    result.problems.append(
                        (number, "the first record does not start the chain")
                    )
                if expected_start is not None and prev != expected_start:
                    result.problems.append(
                        (number, "the record does not continue the older file")
                    )
            else:
                if seq != expected_seq:
                    result.problems.append(
                        (number, f"sequence number {seq}, expected {expected_seq}")
                    )
                if prev != previous:
                    result.problems.append(
                        (number, "the record does not refer to the record before it")
                    )
            if _digest(prev, seq, _canonical(data), key) != digest:
                result.problems.append((number, "the contents were changed"))
            else:
                result.records += 1
                result.last_seq = seq
            previous = digest
            expected_seq = seq + 1
    return result
