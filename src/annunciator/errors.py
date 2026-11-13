"""Coded exceptions.

A coded exception is an exception that has a message code, a probable
cause and a remedy. All coded exceptions are subclasses of
:class:`CodedError`.

You can use the classes of this module directly. You can also make your
own subclasses. Set the class attribute ``default_code`` to give a
standard message code to a subclass.

Examples
--------
>>> from annunciator import CodedError, MessageCatalogue
>>> cat = MessageCatalogue("DOC", replace=True)
>>> _ = cat.define(7, "E", "The detector '{name}' does not answer.",
...                remedy="Make sure that the detector has power.")
>>> class DetectorError(CodedError):
...     default_code = "DOC-E-0007"
>>> error = DetectorError(name="HPGe-2")
>>> str(error)
"[DOC-E-0007] The detector 'HPGe-2' does not answer."
>>> error.remedy
'Make sure that the detector has power.'
"""

from __future__ import annotations

from typing import Any, ClassVar, List, Mapping, Optional, Sequence

from ._coded import CodedMixin
from .levels import Severity

__all__ = [
    "CodedError",
    "ConfigurationError",
    "ValidationError",
    "DataError",
    "ResourceError",
    "ResourceNotFoundError",
    "ResourceAccessError",
    "OperationError",
    "OperationTimeoutError",
    "RetryExhaustedError",
    "DependencyError",
    "InternalError",
    "CatalogueError",
    "AggregateError",
]


class CodedError(CodedMixin, Exception):
    """Base class of all coded exceptions.

    Parameters
    ----------
    message
        The message text. If you give ``None`` and the code has a
        definition, the class makes the text from the definition.
    code
        The message code. If you give ``None``, the class uses
        ``default_code``.
    context
        More data about the conditions when the error occurred.
    cause
        The probable cause. This text replaces the cause of the
        definition.
    remedy
        The corrective action. This text replaces the remedy of the
        definition.
    **fields
        The values for the replacement fields of the message text.

    Notes
    -----
    The attribute ``cause`` is a text for the user. It is different from
    the attribute ``__cause__`` that Python sets for ``raise ... from``.
    """

    default_severity: ClassVar[Severity] = Severity.ERROR
    #: The exit status that a command-line program can return for this error.
    exit_code: ClassVar[int] = 1

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
        cause: Optional[str] = None,
        remedy: Optional[str] = None,
        **fields: Any,
    ) -> None:
        text = self._init_coded(message, code, context, cause, remedy, fields)
        super().__init__(text)

    def __reduce__(self):
        return (_rebuild, (type(self), self.message, dict(self.__dict__)))


def _rebuild(cls, message, state):
    """Make a coded error again from pickle data."""
    obj = cls.__new__(cls)
    Exception.__init__(obj, message)
    obj.__dict__.update(state)
    return obj


class ConfigurationError(CodedError):
    """A configuration value or a configuration file is not correct."""

    exit_code = 78


class ValidationError(CodedError, ValueError):
    """An input value is not correct.

    The class is also a subclass of :class:`ValueError`.
    """

    exit_code = 65


class DataError(CodedError):
    """The contents of a data set are not correct or not complete."""

    exit_code = 65


class ResourceError(CodedError):
    """A file, a device or a network resource caused an error."""

    exit_code = 74


class ResourceNotFoundError(ResourceError):
    """A necessary resource does not exist."""

    exit_code = 66


class ResourceAccessError(ResourceError):
    """The program does not have access to a resource."""

    exit_code = 77


class OperationError(CodedError):
    """An operation did not complete."""


class OperationTimeoutError(OperationError):
    """An operation did not complete in the permitted time."""

    default_code = "ANN-E-0310"
    exit_code = 75


class RetryExhaustedError(OperationError):
    """All attempts of an operation failed.

    The :func:`~annunciator.handling.retry` decorator raises this
    exception. The attribute ``__cause__`` contains the last exception.
    """

    default_code = "ANN-E-0302"
    exit_code = 75


class DependencyError(CodedError):
    """A necessary package, program or service is not available."""

    exit_code = 69


class InternalError(CodedError):
    """The program found a defect in its own logic."""

    default_severity = Severity.CRITICAL
    exit_code = 70


class CatalogueError(CodedError):
    """A message code or a message catalogue is not correct."""

    exit_code = 70


class AggregateError(CodedError):
    """A group of errors that occurred in one operation.

    The :class:`~annunciator.handling.ErrorCollector` class raises this
    exception.

    Parameters
    ----------
    message
        The message text.
    errors
        The exceptions of the group.
    **kwargs
        The other parameters of :class:`CodedError`.

    Attributes
    ----------
    errors : list of BaseException
        The exceptions of the group.
    """

    default_code = "ANN-E-0304"

    def __init__(
        self,
        message: Optional[str] = None,
        errors: Sequence[BaseException] = (),
        **kwargs: Any,
    ) -> None:
        self.errors: List[BaseException] = list(errors)
        kwargs.setdefault("count", len(self.errors))
        super().__init__(message, **kwargs)

    def describe(self) -> str:
        """Return the message and one line for each error of the group."""
        lines = [super().describe()]
        for index, error in enumerate(self.errors, start=1):
            lines.append(f"  {index}. {type(error).__name__}: {error}")
        return "\n".join(lines)
