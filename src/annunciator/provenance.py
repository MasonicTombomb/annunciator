"""Run records and run manifests.

A run is one complete operation of a program, for example one
measurement or one simulation. This module records the data that are
necessary to do the same run again:

* the versions of Python and of the important packages,
* the revision of the source code,
* the computer, the command line and the configuration,
* the seed of the random number generator,
* the start time, the duration and the result.

Examples
--------
>>> from annunciator.provenance import collect_manifest
>>> manifest = collect_manifest(seed=42, git=False)
>>> manifest["seed"], sorted(manifest)[:3]
(42, ['annunciator', 'argv', 'cwd'])
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

from ._version import __version__
from .context import bind, unbind
from .events import json_default
from .handling import LoggerLike, _resolve_logger
from .levels import Severity
from .logger import record_suppressed_summary, reset_occurrences

__all__ = ["collect_manifest", "git_revision", "Run", "start_run"]


def git_revision(path: Union[str, Path, None] = None) -> Optional[Dict[str, Any]]:
    """Return the revision of the git repository that contains a path.

    Parameters
    ----------
    path
        A directory in the repository. The default is the current
        directory.

    Returns
    -------
    dict or None
        The keys ``commit`` and ``dirty``. ``dirty`` is ``True`` if the
        repository has changes that are not committed. The function
        returns ``None`` if git is not available or the path is not in
        a repository.
    """
    cwd = str(path) if path is not None else None

    def run(*args: str) -> Optional[str]:
        try:
            done = subprocess.run(
                ("git",) + args, cwd=cwd, capture_output=True, text=True,
                timeout=3, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    if not commit:
        return None
    status = run("status", "--porcelain")
    return {"commit": commit, "dirty": bool(status)}


def _package_versions(packages: Iterable[str]) -> Dict[str, str]:
    from importlib import metadata

    versions = {}
    for name in packages:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def collect_manifest(
    *,
    packages: Iterable[str] = (),
    seed: Any = None,
    git: bool = True,
    include_user: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Collect the data that identify the environment of a run.

    Parameters
    ----------
    packages
        The names of the installed packages whose versions you must
        record, for example ``("numpy", "scipy")``.
    seed
        The seed of the random number generator. The function only
        records the value. It does not set the seed.
    git
        If ``True``, record the git revision of the current directory.
    include_user
        If ``True``, record the login name of the user. The default is
        ``False`` because the name is personal data.
    extra
        More items for the manifest, for example the parameters of the
        run.

    Returns
    -------
    dict
        The manifest. JSON can contain all its values.
    """
    from .config import current_config

    manifest: Dict[str, Any] = {
        "annunciator": __version__,
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "executable": sys.executable,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "pid": os.getpid(),
        "started": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    if packages:
        manifest["packages"] = _package_versions(packages)
    if seed is not None:
        manifest["seed"] = seed
    if git:
        revision = git_revision()
        if revision is not None:
            manifest["git"] = revision
    if include_user:
        import getpass

        try:
            manifest["user"] = getpass.getuser()
        except Exception:  # noqa: BLE001 - no login name available
            pass
    config = current_config()
    if config is not None:
        text = json.dumps(config.to_dict(), sort_keys=True, default=json_default)
        manifest["config_hash"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    if extra:
        manifest["extra"] = json.loads(json.dumps(extra, default=json_default))
    return manifest


class _Counter(logging.Handler):
    """Handler that counts the warnings and the errors of a run."""

    def __init__(self) -> None:
        super().__init__(int(Severity.WARNING))
        self.warnings = 0
        self.errors = 0
        self.worst = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= int(Severity.ERROR):
            self.errors += 1
        else:
            self.warnings += 1
        self.worst = max(self.worst, record.levelno)


class Run:
    """One run of a program.

    Do not make an instance directly. Use :func:`start_run`. A run is
    also a context manager.

    Attributes
    ----------
    name : str
        The name of the run.
    run_id : str
        A unique identifier. All events of the run have the context
        field ``run_id``.
    manifest : dict
        The manifest of the run.
    status : str
        ``"running"``, ``"completed"`` or ``"failed"``.
    """

    def __init__(
        self,
        name: str,
        manifest: Dict[str, Any],
        logger: LoggerLike = None,
    ) -> None:
        self.name = name
        self.run_id = uuid.uuid4().hex[:12]
        self.manifest = manifest
        self.status = "running"
        self.elapsed = 0.0
        self._log = _resolve_logger(logger)
        self._start = time.monotonic()
        self._counter = _Counter()
        logging.getLogger().addHandler(self._counter)
        reset_occurrences()
        bind(run_id=self.run_id)
        self._log.event("ANN-N-0401", run=name, manifest=manifest)

    @property
    def errors(self) -> int:
        """The number of events of the severity ``ERROR`` or higher."""
        return self._counter.errors

    @property
    def warnings(self) -> int:
        """The number of events of the severity ``WARNING``."""
        return self._counter.warnings

    @property
    def exit_code(self) -> int:
        """An exit status for the program: 0, 1 or 2.

        The value is 0 if the run has no errors, 1 if the worst
        severity is ``ERROR`` and 2 if it is ``CRITICAL``.
        """
        if self._counter.worst >= int(Severity.CRITICAL):
            return 2
        return 1 if self._counter.worst >= int(Severity.ERROR) else 0

    def save_manifest(self, path: Union[str, Path]) -> Path:
        """Write the manifest and the result of the run to a JSON file.

        Returns
        -------
        pathlib.Path
            The path of the file.
        """
        data = dict(self.manifest)
        data.update(
            run=self.name,
            run_id=self.run_id,
            status=self.status,
            elapsed=round(self.elapsed, 3),
            errors=self.errors,
            warnings=self.warnings,
        )
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            json.dumps(data, indent=2, default=json_default) + "\n",
            encoding="utf-8",
        )
        return file

    def finish(self, exc: Optional[BaseException] = None) -> None:
        """Record the end of the run.

        The method records the code ``ANN-N-0402`` for a normal end, or
        the code ``ANN-E-0403`` for an end because of an exception. It
        also records the summary of rejected repeated messages.

        Parameters
        ----------
        exc
            The exception that stopped the run, or ``None``.
        """
        if self.status != "running":
            return
        self.elapsed = time.monotonic() - self._start
        shown = f"{self.elapsed:.3f}"
        record_suppressed_summary(self._log)
        if exc is None:
            self.status = "completed"
            self._log.event(
                "ANN-N-0402", run=self.name, elapsed=shown,
                errors=self.errors, warnings=self.warnings,
            )
        else:
            self.status = "failed"
            self._log.event(
                "ANN-E-0403",
                exc_info=(type(exc), exc, exc.__traceback__),
                run=self.name, elapsed=shown,
                exc_type=type(exc).__qualname__, exc_message=str(exc),
            )
        logging.getLogger().removeHandler(self._counter)
        unbind("run_id")

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None and isinstance(exc, (KeyboardInterrupt, SystemExit)):
            self.finish()
        else:
            self.finish(exc)
        return False


def start_run(
    name: Optional[str] = None,
    *,
    packages: Iterable[str] = (),
    seed: Any = None,
    git: bool = True,
    include_user: bool = False,
    logger: LoggerLike = None,
    **extra: Any,
) -> Run:
    """Start a run and record its manifest.

    The function records the code ``ANN-N-0401``. The field
    ``manifest`` of the event contains the manifest.
    The function also sets the state of the log methods ``once``,
    ``every`` and ``throttle`` to its initial condition.

    Parameters
    ----------
    name
        The name of the run. The default is the name of the program
        file.
    packages
        The names of the packages whose versions you must record.
    seed
        The seed of the random number generator.
    git
        If ``True``, record the git revision.
    include_user
        If ``True``, record the login name of the user.
    logger
        A structured logger, a standard logger or a logger name.
    **extra
        More items for the manifest, for example the parameters of the
        run.

    Returns
    -------
    Run
        The run. Use it as a context manager, or call
        :meth:`Run.finish` at the end.

    Examples
    --------
    >>> from annunciator.provenance import start_run
    >>> with start_run("demo", git=False, live_time=600) as run:
    ...     pass
    >>> run.status, run.exit_code
    ('completed', 0)
    """
    if name is None:
        name = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "run"
    manifest = collect_manifest(
        packages=packages, seed=seed, git=git,
        include_user=include_user, extra=extra or None,
    )
    return Run(name, manifest, logger)
