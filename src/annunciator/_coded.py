"""Shared behaviour of coded errors and coded warnings (internal module)."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Mapping, Optional

from .catalogue import lookup
from .levels import Severity


class CodedMixin:
    """Behaviour that coded errors and coded warnings have in common.

    Attributes
    ----------
    code : str or None
        The message code.
    message : str
        The message text with the field values.
    severity : Severity
        The severity of the related event.
    cause : str
        The probable cause.
    remedy : str
        The corrective action.
    fields : dict
        The values of the replacement fields.
    context : dict
        More data about the conditions when the event occurred.
    """

    #: Message code that the class uses when you do not give a code.
    default_code: ClassVar[Optional[str]] = None
    #: Severity that the class uses when the code has no definition.
    default_severity: ClassVar[Severity] = Severity.ERROR

    code: Optional[str]
    message: str
    severity: Severity
    cause: str
    remedy: str
    fields: Dict[str, Any]
    context: Dict[str, Any]

    def _init_coded(
        self,
        message: Optional[str],
        code: Optional[str],
        context: Optional[Mapping[str, Any]],
        cause: Optional[str],
        remedy: Optional[str],
        fields: Mapping[str, Any],
    ) -> str:
        """Set the attributes and return the message text."""
        code = code or self.default_code
        definition = lookup(code)
        self.code = code
        self.fields = dict(fields)
        self.context = dict(context or {})
        if definition is not None:
            text = definition.format(**fields) if message is None else message
            self.severity = definition.severity
            self.cause = cause or definition.cause
            self.remedy = remedy or definition.remedy
        else:
            text = "" if message is None else str(message)
            self.severity = self.default_severity
            self.cause = cause or ""
            self.remedy = remedy or ""
        self.message = text
        return text

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def with_context(self, **values: Any):
        """Add context data and return the same object.

        Examples
        --------
        >>> from annunciator import CodedError
        >>> error = CodedError("No data").with_context(sample="S-1")
        >>> error.context
        {'sample': 'S-1'}
        """
        self.context.update(values)
        return self

    def describe(self) -> str:
        """Return the message, the cause and the remedy as one text."""
        lines = [str(self)]
        if self.cause:
            lines.append(f"Cause: {self.cause}")
        if self.remedy:
            lines.append(f"Remedy: {self.remedy}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Return the data of the object as a dictionary."""
        data: Dict[str, Any] = {
            "type": type(self).__name__,
            "code": self.code,
            "severity": self.severity.name,
            "message": self.message,
            "cause": self.cause,
            "remedy": self.remedy,
            "fields": dict(self.fields),
            "context": dict(self.context),
        }
        return {key: value for key, value in data.items() if value not in ("", None, {})}
