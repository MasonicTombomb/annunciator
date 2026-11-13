"""Soft checks.

A check examines a condition on data. If the condition is not true, the
check does one of three actions. The parameter ``on_fail`` selects the
action:

``"raise"``
    Raise a :class:`~annunciator.errors.ValidationError` (default).
``"warn"``
    Issue a :class:`~annunciator.warns.DataQualityWarning`. The program
    continues.
``"log"``
    Record a ``WARNING`` event. The program continues.

Each check returns ``True`` if the condition is true. Thus you can use a
check in an ``if`` statement.

Examples
--------
>>> from annunciator.checks import check_range, check_finite
>>> check_range(0.31, 0.0, 1.0, name="dead_time")
True
>>> check_finite([1.0, float("nan")], name="counts", on_fail="log")
False
>>> from annunciator import ValidationError
>>> try:
...     check_range(1.4, 0.0, 1.0, name="dead_time")
... except ValidationError as error:
...     error.code
'ANN-E-0601'
"""

from __future__ import annotations

import math
from typing import Any, Collection, Optional, Tuple, Type, Union

from .errors import CodedError, ValidationError
from .handling import LoggerLike, _resolve_logger
from .warns import CodedWarning, DataQualityWarning, warn

__all__ = [
    "check",
    "check_range",
    "check_finite",
    "check_type",
    "check_not_empty",
    "check_one_of",
]

_ACTIONS = ("raise", "warn", "log")


def _fail(
    number: int,
    on_fail: str,
    error: Type[CodedError],
    category: Type[CodedWarning],
    logger: LoggerLike,
    message: Optional[str],
    code: Optional[str],
    fields: dict,
) -> bool:
    """Do the selected action for a check that failed. Return ``False``."""
    if on_fail not in _ACTIONS:
        raise ValueError("on_fail must be 'raise', 'warn' or 'log'")
    if on_fail == "raise":
        raise error(message, code=code or f"ANN-E-06{number:02d}", **fields)
    soft = code or f"ANN-W-06{10 + number}"
    if on_fail == "warn":
        warn(message, category, code=soft, stacklevel=3, **fields)
    else:
        log = _resolve_logger(logger)
        if message is None:
            log.event(soft, stacklevel=3, **fields)
        else:
            log.warning(message, code=soft, stacklevel=3, **fields)
    return False


def check(
    condition: Any,
    message: Optional[str] = None,
    *,
    name: str = "condition",
    code: Optional[str] = None,
    on_fail: str = "raise",
    error: Type[CodedError] = ValidationError,
    category: Type[CodedWarning] = DataQualityWarning,
    logger: LoggerLike = None,
    **fields: Any,
) -> bool:
    """Examine a condition.

    Parameters
    ----------
    condition
        The value to examine. The check passes if the value is true.
    message
        The message text for a failure. The default is the text of the
        code.
    name
        A name for the check, for the default message.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0606`` or ``ANN-W-0616``.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    error
        The exception class for ``"raise"``.
    category
        The warning class for ``"warn"``.
    logger
        The logger for ``"log"``.
    **fields
        Structured fields for the failure, for example the values that
        the condition used.

    Returns
    -------
    bool
        ``True`` if the check passed.

    Raises
    ------
    ValidationError
        If the check failed and ``on_fail`` is ``"raise"``.
    """
    if condition:
        return True
    fields.setdefault("name", name)
    return _fail(6, on_fail, error, category, logger, message, code, fields)


def check_range(
    value: Any,
    minimum: Any = None,
    maximum: Any = None,
    *,
    name: str = "value",
    inclusive: bool = True,
    on_fail: str = "raise",
    code: Optional[str] = None,
    logger: LoggerLike = None,
) -> bool:
    """Examine if a number is in a range.

    A value that is not a number (NaN) is always out of the range.

    Parameters
    ----------
    value
        The number to examine.
    minimum
        The lower limit, or ``None`` for no lower limit.
    maximum
        The upper limit, or ``None`` for no upper limit.
    name
        The name of the value for the message.
    inclusive
        If ``True``, the limits are permitted values.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0601`` or ``ANN-W-0611``.
    logger
        The logger for ``"log"``.

    Returns
    -------
    bool
        ``True`` if the value is in the range.
    """
    try:
        if inclusive:
            low = minimum is None or value >= minimum
            high = maximum is None or value <= maximum
        else:
            low = minimum is None or value > minimum
            high = maximum is None or value < maximum
        passed = bool(low and high)
    except TypeError:
        passed = False
    if passed:
        return True
    fields = {
        "name": name,
        "value": value,
        "minimum": "no limit" if minimum is None else minimum,
        "maximum": "no limit" if maximum is None else maximum,
    }
    return _fail(
        1, on_fail, ValidationError, DataQualityWarning, logger, None, code, fields
    )


def _count_not_finite(value: Any) -> int:
    if hasattr(value, "__array__"):
        try:
            import numpy

            return int((~numpy.isfinite(numpy.asarray(value, dtype=float))).sum())
        except Exception:  # noqa: BLE001 - go to the general procedure
            pass
    if isinstance(value, (int, float)):
        return 0 if math.isfinite(value) else 1
    count = 0
    for item in value:
        try:
            if not math.isfinite(item):
                count += 1
        except TypeError:
            count += _count_not_finite(item)
    return count


def check_finite(
    value: Any,
    *,
    name: str = "value",
    on_fail: str = "raise",
    code: Optional[str] = None,
    logger: LoggerLike = None,
) -> bool:
    """Examine if all numbers are finite.

    The check fails if the data contain NaN or infinite values. It
    accepts one number, a sequence, a sequence of sequences or a NumPy
    array.

    Parameters
    ----------
    value
        The data to examine.
    name
        The name of the data for the message.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0602`` or ``ANN-W-0612``.
    logger
        The logger for ``"log"``.

    Returns
    -------
    bool
        ``True`` if all numbers are finite.
    """
    count = _count_not_finite(value)
    if count == 0:
        return True
    return _fail(
        2, on_fail, ValidationError, DataQualityWarning, logger, None, code,
        {"name": name, "count": count},
    )


def check_type(
    value: Any,
    expected: Union[type, Tuple[type, ...]],
    *,
    name: str = "value",
    on_fail: str = "raise",
    code: Optional[str] = None,
    logger: LoggerLike = None,
) -> bool:
    """Examine if a value has a permitted type.

    Parameters
    ----------
    value
        The value to examine.
    expected
        A type or a tuple of types.
    name
        The name of the value for the message.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0603`` or ``ANN-W-0613``.
    logger
        The logger for ``"log"``.

    Returns
    -------
    bool
        ``True`` if the value has a permitted type.
    """
    if isinstance(value, expected):
        return True
    kinds = expected if isinstance(expected, tuple) else (expected,)
    return _fail(
        3, on_fail, ValidationError, DataQualityWarning, logger, None, code,
        {
            "name": name,
            "actual": type(value).__name__,
            "expected": " or ".join(kind.__name__ for kind in kinds),
        },
    )


def check_not_empty(
    value: Any,
    *,
    name: str = "value",
    on_fail: str = "raise",
    code: Optional[str] = None,
    logger: LoggerLike = None,
) -> bool:
    """Examine if a sequence, a text or a data set contains items.

    Parameters
    ----------
    value
        The object to examine. ``None`` is empty.
    name
        The name of the object for the message.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0604`` or ``ANN-W-0614``.
    logger
        The logger for ``"log"``.

    Returns
    -------
    bool
        ``True`` if the object contains one or more items.
    """
    try:
        empty = value is None or len(value) == 0
    except TypeError:
        empty = False
    if not empty:
        return True
    return _fail(
        4, on_fail, ValidationError, DataQualityWarning, logger, None, code,
        {"name": name},
    )


def check_one_of(
    value: Any,
    choices: Collection[Any],
    *,
    name: str = "value",
    on_fail: str = "raise",
    code: Optional[str] = None,
    logger: LoggerLike = None,
) -> bool:
    """Examine if a value is one of the permitted values.

    Parameters
    ----------
    value
        The value to examine.
    choices
        The permitted values.
    name
        The name of the value for the message.
    on_fail
        ``"raise"``, ``"warn"`` or ``"log"``.
    code
        Your own message code for a failure. The default is
        ``ANN-E-0605`` or ``ANN-W-0615``.
    logger
        The logger for ``"log"``.

    Returns
    -------
    bool
        ``True`` if the value is one of the permitted values.
    """
    if value in choices:
        return True
    return _fail(
        5, on_fail, ValidationError, DataQualityWarning, logger, None, code,
        {
            "name": name,
            "value": value,
            "choices": ", ".join(repr(item) for item in choices),
        },
    )
