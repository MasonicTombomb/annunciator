"""Coded warnings.

A coded warning is a Python warning that has a message code, a probable
cause and a remedy. Use :func:`warn` to issue a coded warning.

The standard :mod:`warnings` module controls the warnings. Thus the user
can use warning filters to ignore a warning or to change it into an
exception. When the exception hooks are installed, the library records
each warning in the log.

Examples
--------
>>> import warnings
>>> from annunciator import warn, DataQualityWarning
>>> with warnings.catch_warnings(record=True) as caught:
...     warnings.simplefilter("always")
...     warn("The spectrum has only 12 counts.", DataQualityWarning)
>>> str(caught[0].message)
'The spectrum has only 12 counts.'
"""

from __future__ import annotations

import warnings
from typing import Any, ClassVar, Mapping, Optional, Type

from ._coded import CodedMixin
from .levels import Severity

__all__ = [
    "CodedWarning",
    "ConfigurationWarning",
    "DataQualityWarning",
    "PerformanceWarning",
    "DeprecatedFeatureWarning",
    "warn",
]


class CodedWarning(CodedMixin, UserWarning):
    """Base class of all coded warnings.

    The parameters are the same as the parameters of
    :class:`~annunciator.errors.CodedError`.
    """

    default_severity: ClassVar[Severity] = Severity.WARNING

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


class ConfigurationWarning(CodedWarning):
    """A configuration value is permitted but is possibly not correct."""


class DataQualityWarning(CodedWarning):
    """The quality of the input data can cause an incorrect result."""


class PerformanceWarning(CodedWarning):
    """An operation is slower or uses more memory than is usual."""


class DeprecatedFeatureWarning(CodedWarning, DeprecationWarning):
    """The program uses a feature that a future version will remove.

    The class is also a subclass of :class:`DeprecationWarning`.
    """

    default_code = "ANN-W-0309"


def warn(
    message: Optional[str] = None,
    category: Type[CodedWarning] = CodedWarning,
    *,
    code: Optional[str] = None,
    stacklevel: int = 1,
    context: Optional[Mapping[str, Any]] = None,
    **fields: Any,
) -> None:
    """Issue a coded warning.

    Parameters
    ----------
    message
        The message text. If you give ``None``, the function makes the
        text from the definition of the code.
    category
        The warning class. It must be a subclass of
        :class:`CodedWarning`.
    code
        The message code.
    stacklevel
        The number of stack frames between this call and the line that
        the warning must identify. The value 1 identifies the line that
        calls this function.
    context
        More data about the conditions.
    **fields
        The values for the replacement fields of the message text.

    Raises
    ------
    TypeError
        If the category is not a subclass of :class:`CodedWarning`.
    """
    if not (isinstance(category, type) and issubclass(category, CodedWarning)):
        raise TypeError("category must be a subclass of CodedWarning")
    instance = category(message, code=code, context=context, **fields)
    warnings.warn(instance, stacklevel=stacklevel + 1)
