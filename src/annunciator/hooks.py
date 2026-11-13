"""Exception hooks and warning capture.

The hooks record the problems that no code in the program handles:

* exceptions that stop the program,
* exceptions that stop a thread,
* exceptions that Python cannot raise,
* errors that an :mod:`asyncio` event loop reports,
* Python warnings.

The :func:`~annunciator.config.configure` function installs the hooks
when the options ``install_hooks`` and ``capture_warnings`` are set.

Examples
--------
>>> from annunciator import hooks
>>> hooks.install_hooks()
>>> hooks.hooks_installed()
True
>>> hooks.uninstall_hooks()
>>> hooks.hooks_installed()
False
"""

from __future__ import annotations

import asyncio
import sys
import threading
import warnings as _warnings
from typing import Any, Dict, Optional

from .levels import Severity
from .logger import StructuredLogger, get_logger

__all__ = [
    "install_hooks",
    "uninstall_hooks",
    "hooks_installed",
    "install_asyncio_handler",
]

_ORIGINAL: Dict[str, Any] = {}
_LOCK = threading.RLock()
_LOGGER_NAME = "annunciator.hooks"
_WARNINGS_LOGGER_NAME = "py.warnings"


def _logger(logger: Optional[StructuredLogger]) -> StructuredLogger:
    return logger if logger is not None else get_logger(_LOGGER_NAME)


def _record_uncaught(
    log: StructuredLogger, code: str, exc: BaseException, **fields: Any
) -> None:
    """Record an exception that no code caught."""
    if getattr(exc, "code", None) and hasattr(exc, "message"):
        log.report(
            exc, severity=Severity.CRITICAL, force=True, uncaught=True, **fields
        )
    else:
        log.event(
            code,
            exc_info=(type(exc), exc, exc.__traceback__),
            exc_type=type(exc).__qualname__,
            exc_message=str(exc),
            **fields,
        )


def install_hooks(
    logger: Optional[StructuredLogger] = None,
    *,
    exceptions: bool = True,
    threads: bool = True,
    unraisable: bool = True,
    warnings: bool = True,
) -> None:
    """Install the hooks that record unhandled problems.

    Parameters
    ----------
    logger
        The logger for the records. The default is the logger
        ``annunciator.hooks``. Warnings always go to the logger
        ``py.warnings``.
    exceptions
        If ``True``, replace ``sys.excepthook``. The hook records each
        exception that stops the program (``ANN-C-0201``). For a coded
        exception, the hook records the code of the exception with the
        severity ``CRITICAL``.
    threads
        If ``True``, replace ``threading.excepthook`` (``ANN-C-0202``).
    unraisable
        If ``True``, replace ``sys.unraisablehook`` (``ANN-E-0204``).
    warnings
        If ``True``, replace ``warnings.showwarning``. The hook records
        a coded warning with its code. It records all other warnings
        with the code ``ANN-W-0205``.

    Notes
    -----
    The hooks do not record ``KeyboardInterrupt`` and ``SystemExit``.
    The initial hooks handle these exceptions. If you call the function
    again, the function first removes the hooks of the previous call.
    """
    log = _logger(logger)
    with _LOCK:
        uninstall_hooks()

        if exceptions:
            previous_except = sys.excepthook

            def excepthook(exc_type, exc, tb):
                if exc is None or issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
                    previous_except(exc_type, exc, tb)
                    return
                try:
                    _record_uncaught(log, "ANN-C-0201", exc)
                except Exception:  # noqa: BLE001 - last line of defence
                    previous_except(exc_type, exc, tb)

            _ORIGINAL["excepthook"] = previous_except
            sys.excepthook = excepthook

        if threads:
            previous_thread = threading.excepthook

            def thread_hook(args):
                if args.exc_value is None or issubclass(args.exc_type, SystemExit):
                    previous_thread(args)
                    return
                name = args.thread.name if args.thread is not None else "?"
                try:
                    _record_uncaught(log, "ANN-C-0202", args.exc_value, thread=name)
                except Exception:  # noqa: BLE001
                    previous_thread(args)

            _ORIGINAL["threading"] = previous_thread
            threading.excepthook = thread_hook

        if unraisable:
            previous_unraisable = sys.unraisablehook

            def unraisable_hook(args):
                exc = args.exc_value
                if exc is None:
                    previous_unraisable(args)
                    return
                detail = args.err_msg or "Exception ignored"
                if args.object is not None:
                    detail = f"{detail}: {args.object!r}"
                try:
                    log.event(
                        "ANN-E-0204",
                        exc_info=(type(exc), exc, exc.__traceback__),
                        exc_type=type(exc).__qualname__,
                        exc_message=str(exc),
                        detail=detail,
                    )
                except Exception:  # noqa: BLE001
                    previous_unraisable(args)

            _ORIGINAL["unraisable"] = previous_unraisable
            sys.unraisablehook = unraisable_hook

        if warnings:
            previous_show = _warnings.showwarning
            warn_log = get_logger(_WARNINGS_LOGGER_NAME)

            def showwarning(message, category, filename, lineno, file=None, line=None):
                if file is not None:
                    previous_show(message, category, filename, lineno, file, line)
                    return
                where = {"filename": filename, "lineno": lineno}
                try:
                    if getattr(message, "code", None) and hasattr(message, "message"):
                        warn_log.report(
                            message,
                            severity=Severity.WARNING,
                            traceback=False,
                            force=True,
                            category=category.__name__,
                            **where,
                        )
                    else:
                        warn_log.event(
                            "ANN-W-0205",
                            category=category.__name__,
                            text=str(message),
                            **where,
                        )
                except Exception:  # noqa: BLE001
                    previous_show(message, category, filename, lineno, file, line)

            _ORIGINAL["showwarning"] = previous_show
            _warnings.showwarning = showwarning


def uninstall_hooks() -> None:
    """Remove the hooks and install the initial hooks again."""
    with _LOCK:
        if "excepthook" in _ORIGINAL:
            sys.excepthook = _ORIGINAL.pop("excepthook")
        if "threading" in _ORIGINAL:
            threading.excepthook = _ORIGINAL.pop("threading")
        if "unraisable" in _ORIGINAL:
            sys.unraisablehook = _ORIGINAL.pop("unraisable")
        if "showwarning" in _ORIGINAL:
            _warnings.showwarning = _ORIGINAL.pop("showwarning")


def hooks_installed() -> bool:
    """Return ``True`` if one or more hooks of the library are installed."""
    return bool(_ORIGINAL)


def install_asyncio_handler(
    loop: Optional[asyncio.AbstractEventLoop] = None,
    logger: Optional[StructuredLogger] = None,
) -> None:
    """Record the errors that an :mod:`asyncio` event loop reports.

    The function sets the exception handler of the loop. The handler
    records each error with the code ``ANN-E-0203``.

    Parameters
    ----------
    loop
        The event loop. The default is the loop that is in operation.
        Call the function in a coroutine if you do not give a loop.
    logger
        The logger for the records.
    """
    log = _logger(logger)
    loop = loop if loop is not None else asyncio.get_running_loop()

    def handler(_loop, context):
        exc = context.get("exception")
        detail = str(context.get("message", "no detail"))
        info = (type(exc), exc, exc.__traceback__) if exc is not None else None
        log.event("ANN-E-0203", exc_info=info, detail=detail)

    loop.set_exception_handler(handler)
