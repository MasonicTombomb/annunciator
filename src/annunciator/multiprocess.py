"""Logs from many processes.

When many processes write to the same log file, the file can become
damaged. The rotation of the file is not safe in this condition. This
module sends the records of all worker processes through a queue to the
primary process. Only the primary process writes the file.

The procedure has three steps:

1. In the primary process, call :func:`~annunciator.config.configure`.
   Then call :func:`start_listener` to get the queue.
2. Start each worker process with :func:`init_worker` as its
   initializer and the queue as its argument.
3. At the end, call :func:`stop_listener`.

Examples
--------
.. code-block:: python

   import multiprocessing

   from annunciator import configure, get_logger
   from annunciator.multiprocess import init_worker, start_listener, stop_listener

   def work(number):
       get_logger("worker").info("Item complete.", item=number)
       return number * number

   if __name__ == "__main__":
       configure(file="logs/run.jsonl", file_format="json")
       queue = start_listener()
       with multiprocessing.Pool(4, init_worker, (queue,)) as pool:
           results = pool.map(work, range(100))
       stop_listener()
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import multiprocessing
import threading
from typing import Any, Optional

from .events import json_default
from .handlers import AsyncQueueHandler
from .levels import Severity, SeverityLike

__all__ = ["ProcessQueueHandler", "start_listener", "stop_listener", "init_worker"]

_LISTENER: Optional[logging.handlers.QueueListener] = None
_QUEUE: Any = None
_LOCK = threading.Lock()


def _plain(value: Any) -> Any:
    """Return a copy of a value that a different process can read."""
    try:
        return json.loads(json.dumps(value, default=json_default))
    except (TypeError, ValueError):
        return str(value)


class ProcessQueueHandler(AsyncQueueHandler):
    """Queue handler for a worker process.

    The handler changes the structured data of each record into simple
    types. Thus the queue can send the record to a different process.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        """Make a record that a different process can read."""
        record = super().prepare(record)
        for name in ("ann_fields", "ann_context", "ann_locals"):
            data = getattr(record, name, None)
            if data is not None:
                setattr(record, name, _plain(data))
        record.ann_remote = True
        return record


class _Relay(logging.Handler):
    """Handler that gives a record from a worker to the local loggers."""

    def emit(self, record: logging.LogRecord) -> None:
        logger = logging.getLogger(record.name)
        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


def start_listener(queue: Any = None) -> Any:
    """Start the thread that writes the records of the worker processes.

    Call this function in the primary process, after
    :func:`~annunciator.config.configure`.

    Parameters
    ----------
    queue
        A queue of the :mod:`multiprocessing` module. If you give
        ``None``, the function makes a queue.

    Returns
    -------
    multiprocessing.Queue
        The queue. Give it to :func:`init_worker` in each worker
        process.
    """
    global _LISTENER, _QUEUE
    with _LOCK:
        if _LISTENER is not None:
            return _QUEUE
        _QUEUE = queue if queue is not None else multiprocessing.Queue(-1)
        _LISTENER = logging.handlers.QueueListener(_QUEUE, _Relay())
        _LISTENER.start()
        return _QUEUE


def stop_listener() -> None:
    """Write the records that are in the queue and stop the thread.

    Call this function after all worker processes stopped. It is safe
    to call the function when no listener is in operation.
    """
    global _LISTENER, _QUEUE
    with _LOCK:
        if _LISTENER is not None:
            _LISTENER.stop()
            _LISTENER = None
            _QUEUE = None


def init_worker(queue: Any, level: SeverityLike = Severity.TRACE) -> None:
    """Configure a worker process to send its records to the queue.

    Use this function as the initializer of a process pool or call it
    at the start of the function that the process runs. The function
    removes all handlers of the root logger in the worker. Then it
    installs one :class:`ProcessQueueHandler`.

    Parameters
    ----------
    queue
        The queue from :func:`start_listener`.
    level
        The minimum severity that the worker sends. The handlers of the
        primary process apply their own levels.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.addHandler(ProcessQueueHandler(queue))
    root.setLevel(int(Severity.coerce(level)))
