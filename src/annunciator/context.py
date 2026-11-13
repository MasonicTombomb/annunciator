"""Context data for events.

Context data are key and value pairs that the library adds to each event.
Typical examples are a run identifier, a sample name, or a user name.

The library keeps the context in a :class:`contextvars.ContextVar`. Thus
each thread and each :mod:`asyncio` task has its own context.

Examples
--------
>>> from annunciator import bind, context, get_context, clear_context
>>> bind(run="R-17")
>>> with context(sample="CeO2-04"):
...     sorted(get_context().items())
[('run', 'R-17'), ('sample', 'CeO2-04')]
>>> get_context()
{'run': 'R-17'}
>>> clear_context()
"""

from __future__ import annotations

import contextlib
import contextvars
import uuid
from typing import Any, Dict, Iterator

__all__ = [
    "bind",
    "unbind",
    "clear_context",
    "get_context",
    "context",
    "new_correlation_id",
]

_CONTEXT: "contextvars.ContextVar[Dict[str, Any]]" = contextvars.ContextVar(
    "annunciator_context", default={}
)


def get_context() -> Dict[str, Any]:
    """Return a copy of the context of the current thread or task."""
    return dict(_CONTEXT.get())


def bind(**values: Any) -> None:
    """Add key and value pairs to the context.

    The pairs stay in the context until you remove them with
    :func:`unbind` or :func:`clear_context`.

    Parameters
    ----------
    **values
        The pairs to add. A new value replaces an old value that has
        the same key.
    """
    merged = dict(_CONTEXT.get())
    merged.update(values)
    _CONTEXT.set(merged)


def unbind(*keys: str) -> None:
    """Remove keys from the context.

    Parameters
    ----------
    *keys
        The keys to remove. The function ignores a key that is not in
        the context.
    """
    merged = dict(_CONTEXT.get())
    for key in keys:
        merged.pop(key, None)
    _CONTEXT.set(merged)


def clear_context() -> None:
    """Remove all pairs from the context."""
    _CONTEXT.set({})


@contextlib.contextmanager
def context(**values: Any) -> Iterator[Dict[str, Any]]:
    """Add pairs to the context for the duration of a ``with`` block.

    At the end of the block, the function sets the context back to its
    initial state.

    Parameters
    ----------
    **values
        The pairs to add.

    Yields
    ------
    dict
        A copy of the context in the block.
    """
    merged = dict(_CONTEXT.get())
    merged.update(values)
    token = _CONTEXT.set(merged)
    try:
        yield dict(merged)
    finally:
        _CONTEXT.reset(token)


def new_correlation_id(key: str = "correlation_id") -> str:
    """Make a unique identifier and add it to the context.

    Use a correlation identifier to find all events of one operation.

    Parameters
    ----------
    key
        The context key for the identifier.

    Returns
    -------
    str
        The identifier. It has 16 hexadecimal characters.
    """
    value = uuid.uuid4().hex[:16]
    bind(**{key: value})
    return value
