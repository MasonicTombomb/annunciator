"""Tools for error handling.

This module contains decorators and context managers that apply a
standard policy to exceptions:

* :func:`handle_errors` and :class:`guard` record an exception. Then
  they raise it again, convert it, or stop it.
* :func:`retry` does an operation again when it fails.
* :class:`ErrorCollector` collects many errors and raises them as one
  group.
* :func:`log_calls` and :func:`timed` record calls and durations.
* :func:`deprecated` issues a warning for an old function.

All decorators accept normal functions and coroutine functions.

Examples
--------
>>> from annunciator import handle_errors
>>> @handle_errors(ZeroDivisionError, reraise=False, default=0.0)
... def ratio(a, b):
...     return a / b
>>> ratio(1, 0)
0.0
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import random
import time
from typing import (
    Any,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .errors import AggregateError, CodedError, RetryExhaustedError
from .levels import Severity, SeverityLike
from .logger import StructuredLogger, get_logger
from .warns import DeprecatedFeatureWarning, warn

__all__ = [
    "handle_errors",
    "guard",
    "retry",
    "log_calls",
    "timed",
    "ErrorCollector",
    "deprecated",
]

F = TypeVar("F", bound=Callable[..., Any])
LoggerLike = Union[StructuredLogger, logging.Logger, str, None]
ExcTypes = Tuple[Type[BaseException], ...]
WrapLike = Union[Type[BaseException], Callable[[BaseException], BaseException], None]


def _resolve_logger(logger: LoggerLike, func: Any = None) -> StructuredLogger:
    """Return a structured logger for a logger, a name or a function."""
    if isinstance(logger, StructuredLogger):
        return logger
    if isinstance(logger, logging.Logger):
        return StructuredLogger(logger)
    if isinstance(logger, str):
        return get_logger(logger)
    module = getattr(func, "__module__", None)
    return get_logger(module or "annunciator")


def _convert(
    exc: BaseException, wrap: WrapLike, operation: str
) -> Optional[BaseException]:
    """Return the exception that replaces ``exc``, or ``None``."""
    if wrap is None:
        return None
    if isinstance(wrap, type) and issubclass(wrap, CodedError):
        context = {
            "operation": operation,
            "original_type": type(exc).__qualname__,
        }
        if wrap.default_code:
            return wrap(context=context, operation=operation, reason=str(exc))
        return wrap(str(exc), context=context)
    if isinstance(wrap, type):
        return wrap(str(exc))
    return wrap(exc)


def _fail(
    exc: BaseException,
    log: StructuredLogger,
    severity: Optional[SeverityLike],
    operation: str,
    on_error: Optional[Callable[[BaseException], Any]],
    wrap: WrapLike,
) -> Optional[BaseException]:
    """Record a failure and return the replacement exception, if any."""
    log.report(exc, severity=severity, operation=operation, stacklevel=3)
    if on_error is not None:
        on_error(exc)
    return _convert(exc, wrap, operation)


def handle_errors(
    *exceptions: Type[BaseException],
    logger: LoggerLike = None,
    severity: Optional[SeverityLike] = None,
    operation: Optional[str] = None,
    reraise: bool = True,
    default: Any = None,
    wrap: WrapLike = None,
    on_error: Optional[Callable[[BaseException], Any]] = None,
) -> Callable[[F], F]:
    """Decorator that applies an error policy to a function.

    When the function raises one of the given exceptions, the decorator
    does these steps:

    1. It records the exception with
       :meth:`~annunciator.logger.StructuredLogger.report`.
    2. It calls ``on_error``, if you gave it.
    3. If you gave ``wrap``, it raises the new exception from the
       initial exception.
    4. If ``reraise`` is ``True``, it raises the initial exception
       again.
    5. If not, it returns ``default``.

    Parameters
    ----------
    *exceptions
        The exception classes to handle. The default is
        :class:`Exception`.
    logger
        A structured logger, a standard logger or a logger name. The
        default is the logger of the module of the function.
    severity
        The severity of the record. The default is the severity of the
        exception, or ``ERROR``.
    operation
        The name of the operation for the record. The default is the
        qualified name of the function.
    reraise
        If ``True``, raise the exception again after the record.
    default
        The value to return when ``reraise`` is ``False``.
    wrap
        An exception class, or a function that makes an exception from
        the initial exception. A :class:`~annunciator.errors.CodedError`
        subclass gets the fields ``operation`` and ``reason``.
    on_error
        A function that the decorator calls with the exception.

    Returns
    -------
    callable
        The decorator.

    Examples
    --------
    >>> from annunciator import handle_errors, DataError
    >>> @handle_errors(KeyError, wrap=DataError)
    ... def channel(spectrum, index):
    ...     return spectrum[index]
    >>> try:
    ...     channel({}, 7)
    ... except DataError as error:
    ...     type(error.__cause__).__name__
    'KeyError'
    """
    exc_types: ExcTypes = exceptions or (Exception,)

    def decorator(func: F) -> F:
        log = _resolve_logger(logger, func)
        name = operation or getattr(func, "__qualname__", repr(func))

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except exc_types as exc:
                    new = _fail(exc, log, severity, name, on_error, wrap)
                    if new is not None:
                        raise new from exc
                    if reraise:
                        raise
                    return default

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exc_types as exc:
                new = _fail(exc, log, severity, name, on_error, wrap)
                if new is not None:
                    raise new from exc
                if reraise:
                    raise
                return default

        return wrapper  # type: ignore[return-value]

    return decorator


class guard:
    """Context manager that applies an error policy to a block.

    The policy is the same as the policy of :func:`handle_errors`. A
    block cannot return a default value. Thus, when ``reraise`` is
    ``False``, the program continues after the block.

    Parameters
    ----------
    *exceptions
        The exception classes to handle. The default is
        :class:`Exception`.
    operation
        The name of the operation for the record.
    logger
        A structured logger, a standard logger or a logger name.
    severity
        The severity of the record.
    reraise
        If ``True``, raise the exception again after the record.
    wrap
        An exception class, or a function that makes an exception.
    on_error
        A function that the context manager calls with the exception.

    Attributes
    ----------
    exception : BaseException or None
        The exception that the block raised.

    Examples
    --------
    >>> from annunciator import guard
    >>> with guard(ValueError, operation="parse", reraise=False) as g:
    ...     value = int("12a")
    >>> g.failed
    True
    >>> type(g.exception).__name__
    'ValueError'
    """

    def __init__(
        self,
        *exceptions: Type[BaseException],
        operation: str = "block",
        logger: LoggerLike = None,
        severity: Optional[SeverityLike] = None,
        reraise: bool = True,
        wrap: WrapLike = None,
        on_error: Optional[Callable[[BaseException], Any]] = None,
    ) -> None:
        self._exc_types: ExcTypes = exceptions or (Exception,)
        self._operation = operation
        self._log = _resolve_logger(logger)
        self._severity = severity
        self._reraise = reraise
        self._wrap = wrap
        self._on_error = on_error
        self.exception: Optional[BaseException] = None

    @property
    def failed(self) -> bool:
        """``True`` if the block raised a handled exception."""
        return self.exception is not None

    def __enter__(self) -> "guard":
        self.exception = None
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None or not isinstance(exc, self._exc_types):
            return False
        self.exception = exc
        new = _fail(
            exc, self._log, self._severity, self._operation,
            self._on_error, self._wrap,
        )
        if new is not None:
            raise new from exc
        return not self._reraise

    async def __aenter__(self) -> "guard":
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return self.__exit__(exc_type, exc, tb)


def retry(
    *exceptions: Type[BaseException],
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: float = 0.0,
    logger: LoggerLike = None,
    operation: Optional[str] = None,
    on_retry: Optional[Callable[[BaseException, int], Any]] = None,
    reraise: bool = False,
    sleep: Optional[Callable[[float], Any]] = None,
) -> Callable[[F], F]:
    """Decorator that does a function again when it fails.

    The delay before attempt ``n + 1`` is
    ``min(delay * backoff ** (n - 1), max_delay)`` seconds. The
    decorator records each failed attempt with the code ``ANN-W-0301``.
    When all attempts fail, it records the code ``ANN-E-0302``.

    Parameters
    ----------
    *exceptions
        The exception classes that start a new attempt. The default is
        :class:`Exception`.
    attempts
        The maximum number of attempts. The minimum is 1.
    delay
        The delay in seconds before the second attempt.
    backoff
        The factor that increases the delay after each attempt.
    max_delay
        The maximum delay in seconds.
    jitter
        A fraction from 0 to 1. The decorator adds a random time of up
        to this fraction of the delay.
    logger
        A structured logger, a standard logger or a logger name.
    operation
        The name of the operation for the records.
    on_retry
        A function that the decorator calls before each delay. It gets
        the exception and the attempt number.
    reraise
        If ``True``, raise the last exception when all attempts fail.
        If ``False``, raise
        :class:`~annunciator.errors.RetryExhaustedError` from the last
        exception.
    sleep
        A function that waits for the given number of seconds. Use this
        parameter in tests. For a coroutine function, the default is
        :func:`asyncio.sleep`.

    Raises
    ------
    ValueError
        If a parameter is out of its range.

    Examples
    --------
    >>> from annunciator import retry
    >>> calls = []
    >>> @retry(OSError, attempts=3, delay=0.0)
    ... def read():
    ...     calls.append(1)
    ...     if len(calls) < 3:
    ...         raise OSError("busy")
    ...     return "data"
    >>> read()
    'data'
    >>> len(calls)
    3
    """
    if attempts < 1:
        raise ValueError("attempts must be 1 or more")
    if delay < 0 or backoff < 1 or max_delay < 0 or not 0 <= jitter <= 1:
        raise ValueError("delay, backoff, max_delay or jitter is out of range")
    exc_types: ExcTypes = exceptions or (Exception,)

    def wait_time(attempt: int) -> float:
        wait = min(delay * backoff ** (attempt - 1), max_delay)
        if jitter:
            wait += random.uniform(0.0, jitter * wait)
        return wait

    def decorator(func: F) -> F:
        log = _resolve_logger(logger, func)
        name = operation or getattr(func, "__qualname__", repr(func))

        def failed(exc: BaseException, attempt: int) -> Optional[float]:
            """Record a failed attempt. Return the delay, or ``None``."""
            reason = str(exc).rstrip(".") or type(exc).__qualname__
            if attempt >= attempts:
                log.event(
                    "ANN-E-0302",
                    exc_info=(type(exc), exc, exc.__traceback__),
                    stacklevel=3,
                    operation=name,
                    attempts=attempts,
                    reason=reason,
                )
                return None
            wait = wait_time(attempt)
            log.event(
                "ANN-W-0301",
                stacklevel=3,
                attempt=attempt,
                attempts=attempts,
                operation=name,
                reason=reason,
                delay=f"{wait:.2f}",
            )
            if on_retry is not None:
                on_retry(exc, attempt)
            return wait

        def exhausted(exc: BaseException) -> RetryExhaustedError:
            return RetryExhaustedError(
                operation=name,
                attempts=attempts,
                reason=str(exc).rstrip(".") or type(exc).__qualname__,
            )

        if inspect.iscoroutinefunction(func):
            async_sleep = sleep or asyncio.sleep

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attempt = 0
                while True:
                    attempt += 1
                    try:
                        return await func(*args, **kwargs)
                    except exc_types as exc:
                        wait = failed(exc, attempt)
                        if wait is None:
                            if reraise:
                                raise
                            raise exhausted(exc) from exc
                    result = async_sleep(wait)
                    if inspect.isawaitable(result):
                        await result

            return async_wrapper  # type: ignore[return-value]

        sync_sleep = sleep or time.sleep

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except exc_types as exc:
                    wait = failed(exc, attempt)
                    if wait is None:
                        if reraise:
                            raise
                        raise exhausted(exc) from exc
                sync_sleep(wait)

        return wrapper  # type: ignore[return-value]

    return decorator


def log_calls(
    logger: LoggerLike = None,
    *,
    severity: SeverityLike = Severity.DEBUG,
    arguments: bool = False,
    result: bool = False,
) -> Callable[[F], F]:
    """Decorator that records the start and the end of each call.

    The decorator records the start with the code ``ANN-D-0306`` and the
    end with the code ``ANN-D-0307``. The end record contains the
    duration.

    Parameters
    ----------
    logger
        A structured logger, a standard logger or a logger name.
    severity
        The severity of the records.
    arguments
        If ``True``, record the arguments as the fields ``args`` and
        ``kwargs``. Do not use this option for secret data.
    result
        If ``True``, record the return value as the field ``result``.
    """
    level = Severity.coerce(severity)

    def decorator(func: F) -> F:
        log = _resolve_logger(logger, func)
        name = getattr(func, "__qualname__", repr(func))

        def before(args: tuple, kwargs: dict) -> float:
            if log.is_enabled_for(level):
                fields = {}
                if arguments:
                    fields = {"args": repr(args), "kwargs": repr(kwargs)}
                log.log(
                    level, "The call of '%s' started.", name,
                    code="ANN-D-0306", stacklevel=3, function=name, **fields,
                )
            return time.perf_counter()

        def after(start: float, value: Any) -> None:
            if log.is_enabled_for(level):
                elapsed = time.perf_counter() - start
                fields = {"result": repr(value)} if result else {}
                log.log(
                    level, "The call of '%s' completed in %.6f s.", name, elapsed,
                    code="ANN-D-0307", stacklevel=3, function=name,
                    elapsed=round(elapsed, 6), **fields,
                )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = before(args, kwargs)
                value = await func(*args, **kwargs)
                after(start, value)
                return value

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = before(args, kwargs)
            value = func(*args, **kwargs)
            after(start, value)
            return value

        return wrapper  # type: ignore[return-value]

    return decorator


class timed:
    """Context manager that records the duration of a block.

    At the end of the block, the context manager records the code
    ``ANN-I-0308``. If the duration is more than ``warn_after``, it
    records the code ``ANN-W-0305``.

    Parameters
    ----------
    operation
        The name of the operation for the record.
    logger
        A structured logger, a standard logger or a logger name.
    severity
        The severity of the normal record.
    warn_after
        A limit in seconds, or ``None`` for no limit.
    **fields
        More structured fields for the record.

    Attributes
    ----------
    elapsed : float
        The duration of the block in seconds.

    Examples
    --------
    >>> from annunciator import timed
    >>> with timed("fit") as timer:
    ...     total = sum(range(1000))
    >>> timer.elapsed >= 0.0
    True
    """

    def __init__(
        self,
        operation: str,
        *,
        logger: LoggerLike = None,
        severity: SeverityLike = Severity.INFO,
        warn_after: Optional[float] = None,
        **fields: Any,
    ) -> None:
        self.operation = operation
        self._log = _resolve_logger(logger)
        self._severity = Severity.coerce(severity)
        self._warn_after = warn_after
        self._fields = fields
        self._start = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "timed":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.elapsed = time.perf_counter() - self._start
        if exc is not None:
            return False
        shown = f"{self.elapsed:.3f}"
        if self._warn_after is not None and self.elapsed > self._warn_after:
            self._log.event(
                "ANN-W-0305",
                stacklevel=2,
                operation=self.operation,
                elapsed=shown,
                limit=f"{self._warn_after:.3f}",
                **self._fields,
            )
        else:
            self._log.log(
                self._severity,
                "The operation '%s' completed in %s s.",
                self.operation,
                shown,
                code="ANN-I-0308",
                stacklevel=2,
                operation=self.operation,
                elapsed=round(self.elapsed, 6),
                **self._fields,
            )
        return False


class ErrorCollector:
    """Object that collects errors and warnings of one operation.

    Use a collector when an operation must continue after an error, for
    example when a program examines many files. At the end, the
    collector can raise all errors as one
    :class:`~annunciator.errors.AggregateError`.

    Parameters
    ----------
    operation
        The name of the operation.
    logger
        A structured logger, a standard logger or a logger name.
    record
        If ``True``, record each error and each warning in the log
        when the collector gets it.

    Attributes
    ----------
    errors : list of BaseException
        The collected errors.
    warnings : list of str
        The collected warning texts.

    Examples
    --------
    >>> from annunciator import ErrorCollector, AggregateError
    >>> collector = ErrorCollector("import", record=False)
    >>> for text in ("1", "x", "3", "y"):
    ...     with collector.catch(ValueError):
    ...         number = int(text)
    >>> len(collector.errors)
    2
    >>> try:
    ...     collector.raise_if_errors()
    ... except AggregateError as error:
    ...     error.message
    "2 errors occurred in 'import'."
    """

    def __init__(
        self,
        operation: str = "operation",
        *,
        logger: LoggerLike = None,
        record: bool = True,
    ) -> None:
        self.operation = operation
        self._log = _resolve_logger(logger)
        self._record = record
        self.errors: List[BaseException] = []
        self.warnings: List[str] = []

    def __repr__(self) -> str:
        return (
            f"ErrorCollector({self.operation!r}, errors={len(self.errors)}, "
            f"warnings={len(self.warnings)})"
        )

    @property
    def ok(self) -> bool:
        """``True`` if the collector has no errors."""
        return not self.errors

    def add(self, error: Union[BaseException, str], **context: Any) -> None:
        """Add an error to the collector.

        Parameters
        ----------
        error
            An exception or a message text. The collector changes a text
            into a :class:`~annunciator.errors.CodedError`.
        **context
            Context data for the record.
        """
        exc: BaseException = CodedError(error) if isinstance(error, str) else error
        self.errors.append(exc)
        if self._record:
            self._log.report(
                exc, operation=self.operation, stacklevel=3, **context
            )

    def add_warning(self, message: str, **fields: Any) -> None:
        """Add a warning text to the collector."""
        self.warnings.append(message)
        if self._record:
            self._log.warning(
                message, stacklevel=2,
                operation=self.operation, **fields,
            )

    def catch(self, *exceptions: Type[BaseException], **context: Any) -> "_Catch":
        """Return a context manager that collects exceptions of a block.

        Parameters
        ----------
        *exceptions
            The exception classes to collect. The default is
            :class:`Exception`.
        **context
            Context data for the record.
        """
        return _Catch(self, exceptions or (Exception,), context)

    def raise_if_errors(self) -> None:
        """Raise an :class:`~annunciator.errors.AggregateError` if errors exist.

        Raises
        ------
        AggregateError
            If the collector has one or more errors (``ANN-E-0304``).
        """
        if self.errors:
            raise AggregateError(errors=self.errors, operation=self.operation)

    def summary(self) -> str:
        """Return a text with the number of errors and warnings."""
        lines = [
            f"{self.operation}: {len(self.errors)} errors, "
            f"{len(self.warnings)} warnings"
        ]
        for index, error in enumerate(self.errors, start=1):
            lines.append(f"  E{index}. {type(error).__name__}: {error}")
        for index, text in enumerate(self.warnings, start=1):
            lines.append(f"  W{index}. {text}")
        return "\n".join(lines)

    def __enter__(self) -> "ErrorCollector":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self.raise_if_errors()
        return False

    def __iter__(self) -> Iterator[BaseException]:
        return iter(list(self.errors))


class _Catch:
    """Context manager of :meth:`ErrorCollector.catch`."""

    def __init__(self, collector: ErrorCollector, exc_types: ExcTypes, context: dict):
        self._collector = collector
        self._exc_types = exc_types
        self._context = context

    def __enter__(self) -> ErrorCollector:
        return self._collector

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None or not isinstance(exc, self._exc_types):
            return False
        self._collector.add(exc, **self._context)
        return True


def deprecated(
    since: str,
    *,
    alternative: Optional[str] = None,
    removal: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator that issues a warning when an old function is called.

    The warning has the class
    :class:`~annunciator.warns.DeprecatedFeatureWarning` and the code
    ``ANN-W-0309``.

    Parameters
    ----------
    since
        The version that deprecated the function.
    alternative
        The name of the function to use as a replacement.
    removal
        The version that will remove the function.

    Examples
    --------
    >>> import warnings
    >>> from annunciator import deprecated
    >>> @deprecated("2.0", alternative="load_spectrum")
    ... def read_spectrum():
    ...     return []
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter("always")
    ...     _ = read_spectrum()
    >>> caught[0].message.message
    "'read_spectrum' is deprecated since version 2.0. Use 'load_spectrum'."
    """
    parts = []
    if alternative:
        parts.append(f"Use '{alternative}'.")
    if removal:
        parts.append(f"Version {removal} will remove it.")
    advice = " ".join(parts) or "Do not use it in new code."

    def decorator(func: F) -> F:
        name = getattr(func, "__qualname__", repr(func))

        def notify() -> None:
            warn(
                None,
                DeprecatedFeatureWarning,
                stacklevel=3,
                name=name,
                since=since,
                advice=advice,
            )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                notify()
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            notify()
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
