"""Severity levels.

This module defines the severity levels of the library. The levels agree
with the numeric levels of the standard :mod:`logging` module. The library
adds two levels: ``TRACE`` (5) and ``NOTICE`` (25).

Examples
--------
>>> from annunciator import Severity
>>> Severity.coerce("warn")
<Severity.WARNING: 30>
>>> Severity.WARNING.letter
'W'
"""

from __future__ import annotations

import enum
import logging
from typing import Union

__all__ = ["Severity", "SeverityLike", "register_levels"]


class Severity(enum.IntEnum):
    """Severity of an event.

    Each member has the same numeric value as the related level of the
    :mod:`logging` module. Thus you can give a member to all functions
    that accept a :mod:`logging` level.

    Attributes
    ----------
    TRACE
        Very detailed data for a developer. Value: 5.
    DEBUG
        Data for fault isolation. Value: 10.
    INFO
        Normal progress of the program. Value: 20.
    NOTICE
        A normal event that is important to the user. Value: 25.
    WARNING
        A condition that can cause an incorrect result. Value: 30.
    ERROR
        An operation did not complete. Value: 40.
    CRITICAL
        The program cannot continue. Value: 50.
    """

    TRACE = 5
    DEBUG = 10
    INFO = 20
    NOTICE = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __str__(self) -> str:
        return self.name

    @property
    def letter(self) -> str:
        """The letter that identifies the severity in a message code.

        The letter is the first letter of the name, for example ``W``
        for ``WARNING``.
        """
        return self.name[0]

    @property
    def is_problem(self) -> bool:
        """``True`` if the severity is ``WARNING`` or higher."""
        return self >= Severity.WARNING

    @property
    def is_failure(self) -> bool:
        """``True`` if the severity is ``ERROR`` or higher."""
        return self >= Severity.ERROR

    @classmethod
    def from_letter(cls, letter: str) -> "Severity":
        """Return the severity that a code letter identifies.

        Parameters
        ----------
        letter
            One of ``T``, ``D``, ``I``, ``N``, ``W``, ``E``, ``C``.

        Raises
        ------
        ValueError
            If the letter does not identify a severity.
        """
        for member in cls:
            if member.letter == letter.upper():
                return member
        raise ValueError(f"{letter!r} is not a severity letter")

    @classmethod
    def coerce(cls, value: "SeverityLike") -> "Severity":
        """Convert a value to a :class:`Severity`.

        Parameters
        ----------
        value
            A :class:`Severity`, an integer, a name, or a code letter.
            The names ``WARN``, ``ERR`` and ``FATAL`` are also correct.
            Letter case is not important. An integer between two levels
            gives the lower level.

        Returns
        -------
        Severity
            The related severity.

        Raises
        ------
        ValueError
            If the text does not identify a severity.
        TypeError
            If the type of the value is not correct.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            raise TypeError("a boolean value is not a severity")
        if isinstance(value, int):
            result = cls.TRACE
            for member in cls:
                if member <= value:
                    result = member
            return result
        if isinstance(value, str):
            text = value.strip().upper()
            text = _ALIASES.get(text, text)
            if text in cls.__members__:
                return cls[text]
            if len(text) == 1 and text.isalpha():
                return cls.from_letter(text)
            if text.lstrip("-").isdigit():
                return cls.coerce(int(text))
            raise ValueError(f"{value!r} is not a severity")
        raise TypeError(f"cannot convert {type(value).__name__} to a severity")


_ALIASES = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL"}

#: Types that :meth:`Severity.coerce` accepts.
SeverityLike = Union[Severity, int, str]


def register_levels() -> None:
    """Give the names ``TRACE`` and ``NOTICE`` to the :mod:`logging` module.

    The package calls this function when you import it. It is safe to
    call the function again.
    """
    logging.addLevelName(int(Severity.TRACE), "TRACE")
    logging.addLevelName(int(Severity.NOTICE), "NOTICE")
