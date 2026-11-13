"""Configuration.

The :func:`configure` function installs the handlers, the formatters and
the filters that a :class:`LogConfig` object selects. You can make the
configuration in the program, or read it from a TOML file, a JSON file
or the environment variables.

Examples
--------
>>> from annunciator import LogConfig
>>> config = LogConfig(level="debug", file="run.log", file_format="json")
>>> config.level
'DEBUG'
>>> LogConfig.from_dict({"level": "warning", "console": False}).level
'WARNING'
"""

from __future__ import annotations

import atexit
import dataclasses
import json
import logging
import logging.handlers
import os
import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from .errors import ConfigurationError
from .filters import (
    DEFAULT_REDACT_KEYS,
    ContextFilter,
    DuplicateFilter,
    LocalsFilter,
    RateLimitFilter,
    RedactionFilter,
    SeverityRangeFilter,
)
from .formatters import ColourFormatter, JsonFormatter, PlainFormatter, supports_colour
from .handlers import (
    AsyncQueueHandler,
    ConsoleHandler,
    EventStoreHandler,
    make_file_handler,
)
from .levels import Severity

__all__ = [
    "LogConfig",
    "configure",
    "shutdown",
    "is_configured",
    "current_config",
    "get_store",
    "ENV_PREFIX",
]

#: Prefix of the environment variables that :meth:`LogConfig.from_env` reads.
ENV_PREFIX = "ANNUNCIATOR_"

_CONSOLE_FORMATS = ("auto", "plain", "colour", "json")
_FILE_FORMATS = ("plain", "json")
_ROTATIONS = ("none", "size", "time")
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")


def _bad(option: str, value: Any) -> ConfigurationError:
    return ConfigurationError(code="ANN-E-0002", option=option, value=value)


def _level_name(option: str, value: Any) -> str:
    try:
        return Severity.coerce(value).name
    except (ValueError, TypeError) as exc:
        raise _bad(option, value) from exc


@dataclass
class LogConfig:
    """The configuration of the library.

    All parameters are optional. The configuration reference in the
    user manual gives the same data in a table.

    Parameters
    ----------
    level
        The minimum severity that the library records.
    logger_name
        The name of the logger that gets the handlers. The empty text
        selects the root logger.
    console
        If ``True``, write events to the console.
    console_level
        The minimum severity for the console. ``None`` selects
        ``level``.
    console_format
        ``"auto"``, ``"plain"``, ``"colour"`` or ``"json"``. ``"auto"``
        selects ``"colour"`` on a terminal and ``"plain"`` in all other
        conditions.
    split_streams
        If ``True``, write ``WARNING`` and higher to ``stderr`` and all
        lower severities to ``stdout``. If ``False``, write all events
        to ``stderr``.
    file
        The path of a log file. ``None`` selects no log file.
    file_level
        The minimum severity for the log file. ``None`` selects
        ``level``.
    file_format
        ``"plain"`` or ``"json"``.
    rotate
        ``"none"``, ``"size"`` or ``"time"``.
    max_bytes
        The maximum size of the log file for the rotation by size.
    backup_count
        The number of old log files to keep.
    when
        The interval for the rotation by time, for example
        ``"midnight"``.
    encoding
        The text encoding of the log file.
    utc
        If ``True``, write the time in UTC.
    show_fields
        If ``True``, write the structured fields in plain text.
    show_help
        If ``True``, write the cause and the remedy in plain text.
    show_source
        If ``True``, write the source file and the line number in plain
        text.
    redact_keys
        Parts of field names that identify secret data.
    redact_patterns
        Regular expressions for secret text.
    duplicate_window
        The time window in seconds for the duplicate filter. The value
        0 selects no duplicate filter.
    rate_limit
        The maximum mean number of records each second. The value 0
        selects no rate limit.
    rate_burst
        The maximum number of records at one time for the rate limit.
    store_capacity
        The number of events that the event store keeps. The value 0
        selects no event store.
    capture_warnings
        If ``True``, record Python warnings in the log.
    install_hooks
        If ``True``, record exceptions that no code caught.
    asynchronous
        If ``True``, write the events in a different thread.
    logger_levels
        The minimum severity for named loggers. The keys are logger
        names.
    flight_recorder
        The number of detailed records that the flight recorder keeps
        in memory. The value 0 selects no flight recorder.
    flight_level
        The minimum severity of the records that the flight recorder
        keeps.
    flight_trigger
        The severity that causes the flight recorder to write the kept
        records.
    file_chain
        If ``True``, add integrity data to each record of the log file.
        The option ``file_format`` must be ``"json"``.
    capture_locals
        If ``True``, record the local variables of the last frames of
        each traceback.

    Raises
    ------
    ConfigurationError
        If a value is not permitted (``ANN-E-0002``).
    """

    level: str = "INFO"
    logger_name: str = ""
    console: bool = True
    console_level: Optional[str] = None
    console_format: str = "auto"
    split_streams: bool = True
    file: Optional[str] = None
    file_level: Optional[str] = None
    file_format: str = "plain"
    rotate: str = "size"
    max_bytes: int = 10_000_000
    backup_count: int = 5
    when: str = "midnight"
    encoding: str = "utf-8"
    utc: bool = True
    show_fields: bool = True
    show_help: bool = True
    show_source: bool = False
    redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS
    redact_patterns: Tuple[str, ...] = ()
    duplicate_window: float = 0.0
    rate_limit: float = 0.0
    rate_burst: int = 100
    store_capacity: int = 1000
    capture_warnings: bool = True
    install_hooks: bool = True
    asynchronous: bool = False
    logger_levels: Dict[str, str] = field(default_factory=dict)
    flight_recorder: int = 0
    flight_level: str = "DEBUG"
    flight_trigger: str = "ERROR"
    file_chain: bool = False
    capture_locals: bool = False

    def __post_init__(self) -> None:
        self.level = _level_name("level", self.level)
        self.flight_level = _level_name("flight_level", self.flight_level)
        self.flight_trigger = _level_name("flight_trigger", self.flight_trigger)
        if self.console_level is not None:
            self.console_level = _level_name("console_level", self.console_level)
        if self.file_level is not None:
            self.file_level = _level_name("file_level", self.file_level)
        if self.console_format == "color":
            self.console_format = "colour"
        if self.console_format not in _CONSOLE_FORMATS:
            raise _bad("console_format", self.console_format)
        if self.file_format not in _FILE_FORMATS:
            raise _bad("file_format", self.file_format)
        if self.rotate not in _ROTATIONS:
            raise _bad("rotate", self.rotate)
        if self.file is not None:
            self.file = os.fspath(self.file)
        for name in (
            "console", "split_streams", "utc", "show_fields", "show_help",
            "show_source", "capture_warnings", "install_hooks", "asynchronous",
            "file_chain", "capture_locals",
        ):
            if not isinstance(getattr(self, name), bool):
                raise _bad(name, getattr(self, name))
        for name, minimum in (
            ("max_bytes", 0), ("backup_count", 0), ("rate_burst", 1),
            ("store_capacity", 0), ("flight_recorder", 0),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise _bad(name, value)
        for name in ("duplicate_window", "rate_limit"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
            ):
                raise _bad(name, value)
            setattr(self, name, float(value))
        for name in ("redact_keys", "redact_patterns"):
            value = getattr(self, name)
            if isinstance(value, str) or not all(isinstance(i, str) for i in value):
                raise _bad(name, value)
            setattr(self, name, tuple(value))
        if self.file_chain and self.file_format != "json":
            raise _bad("file_chain", self.file_chain)
        if not isinstance(self.logger_levels, Mapping):
            raise _bad("logger_levels", self.logger_levels)
        self.logger_levels = {
            str(key): _level_name(f"logger_levels.{key}", value)
            for key, value in self.logger_levels.items()
        }

    # -- construction ------------------------------------------------------

    @classmethod
    def option_names(cls) -> Tuple[str, ...]:
        """Return the names of all configuration options."""
        return tuple(item.name for item in dataclasses.fields(cls))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LogConfig":
        """Make a configuration from a dictionary.

        Raises
        ------
        ConfigurationError
            If the dictionary contains an option that is not known
            (``ANN-E-0001``) or a value that is not permitted
            (``ANN-E-0002``).
        """
        names = cls.option_names()
        for key in data:
            if key not in names:
                raise ConfigurationError(code="ANN-E-0001", option=str(key))
        return cls(**dict(data))

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "LogConfig":
        """Read a configuration from a TOML file or a JSON file.

        In a TOML file, the options can be in the table
        ``[tool.annunciator]``, in the table ``[annunciator]`` or at the
        top level. In a JSON file, the options can be in the object
        ``"annunciator"`` or at the top level.

        Raises
        ------
        ConfigurationError
            If the library cannot read the file (``ANN-E-0003``) or does
            not support the file type (``ANN-E-0004``).
        """
        file = Path(path)
        suffix = file.suffix.lower()
        if suffix not in (".toml", ".json"):
            raise ConfigurationError(code="ANN-E-0004", suffix=suffix)
        try:
            if suffix == ".toml":
                from .catalogue import _load_toml

                data = _load_toml(file)
            else:
                data = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("the top level must be a table or an object")
        except Exception as exc:  # noqa: BLE001 - convert to one error type
            raise ConfigurationError(
                code="ANN-E-0003", path=str(file), reason=str(exc)
            ) from exc
        tool = data.get("tool")
        if isinstance(tool, dict) and isinstance(tool.get("annunciator"), dict):
            data = tool["annunciator"]
        elif isinstance(data.get("annunciator"), dict):
            data = data["annunciator"]
        return cls.from_dict(data)

    @classmethod
    def from_env(
        cls,
        environ: Optional[Mapping[str, str]] = None,
        *,
        prefix: str = ENV_PREFIX,
        base: Optional["LogConfig"] = None,
    ) -> "LogConfig":
        """Make a configuration from the environment variables.

        The name of a variable is the prefix and the option name in
        capital letters, for example ``ANNUNCIATOR_LEVEL``. For a
        sequence, divide the items with commas. For ``logger_levels``,
        use the form ``name=LEVEL,name=LEVEL``.

        Parameters
        ----------
        environ
            The mapping to read. The default is ``os.environ``.
        prefix
            The prefix of the variable names.
        base
            A configuration that gives the values for the options that
            are not in the environment.

        Raises
        ------
        ConfigurationError
            If a value is not permitted (``ANN-E-0002``).
        """
        environ = os.environ if environ is None else environ
        values = base.to_dict() if base is not None else {}
        defaults = cls()
        for name in cls.option_names():
            raw = environ.get(prefix + name.upper())
            if raw is None:
                continue
            values[name] = _parse_env(name, raw, getattr(defaults, name))
        return cls(**values)

    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        data = dataclasses.asdict(self)
        data["redact_keys"] = tuple(self.redact_keys)
        data["redact_patterns"] = tuple(self.redact_patterns)
        return data

    def replace(self, **changes: Any) -> "LogConfig":
        """Return a copy of the configuration with changed options.

        Raises
        ------
        ConfigurationError
            If an option is not known (``ANN-E-0001``).
        """
        data = self.to_dict()
        for key in changes:
            if key not in data:
                raise ConfigurationError(code="ANN-E-0001", option=str(key))
        data.update(changes)
        return type(self)(**data)


def _parse_env(name: str, raw: str, default: Any) -> Any:
    """Convert the text of an environment variable to the option type."""
    text = raw.strip()
    try:
        if isinstance(default, bool):
            lowered = text.lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValueError(text)
        if isinstance(default, int):
            return int(text)
        if isinstance(default, float):
            return float(text)
        if isinstance(default, tuple):
            return tuple(item.strip() for item in text.split(",") if item.strip())
        if isinstance(default, dict):
            result = {}
            for item in text.split(","):
                if not item.strip():
                    continue
                key, _, value = item.partition("=")
                if not value:
                    raise ValueError(item)
                result[key.strip()] = value.strip()
            return result
    except ValueError as exc:
        raise _bad(name, raw) from exc
    return text


# --------------------------------------------------------------------------
# Runtime state
# --------------------------------------------------------------------------


class _State:
    config: Optional[LogConfig] = None
    target: Optional[logging.Logger] = None
    handlers: List[logging.Handler] = []
    outputs: List[logging.Handler] = []
    listener: Optional[logging.handlers.QueueListener] = None
    store: Optional[EventStoreHandler] = None
    previous_level: Optional[int] = None
    hooks_by_config: bool = False
    atexit_registered: bool = False


_STATE = _State()
_LOCK = threading.RLock()


def _formatter(kind: str, config: LogConfig, stream_name: str = "stderr"):
    if kind == "json":
        return JsonFormatter()
    if kind == "auto":
        import sys

        kind = "colour" if supports_colour(getattr(sys, stream_name)) else "plain"
    cls = ColourFormatter if kind == "colour" else PlainFormatter
    return cls(
        utc=config.utc,
        show_fields=config.show_fields,
        show_help=config.show_help,
        show_source=config.show_source,
    )


def _add_filters(handler: logging.Handler, config: LogConfig) -> None:
    handler.addFilter(ContextFilter())
    if config.capture_locals:
        handler.addFilter(LocalsFilter())
    if config.redact_keys or config.redact_patterns:
        handler.addFilter(
            RedactionFilter(config.redact_keys, config.redact_patterns)
        )
    if config.duplicate_window > 0:
        handler.addFilter(DuplicateFilter(config.duplicate_window))
    if config.rate_limit > 0:
        handler.addFilter(RateLimitFilter(config.rate_limit, config.rate_burst))


def _build_outputs(config: LogConfig) -> List[logging.Handler]:
    """Make the handlers that write the events."""
    outputs: List[logging.Handler] = []
    base = Severity[config.level]
    if config.console:
        level = int(Severity[config.console_level or config.level])
        if config.split_streams:
            out = ConsoleHandler("stdout")
            out.addFilter(SeverityRangeFilter(maximum=Severity.NOTICE))
            out.setFormatter(_formatter(config.console_format, config, "stdout"))
            out.setLevel(level)
            outputs.append(out)
            err = ConsoleHandler("stderr")
            err.setFormatter(_formatter(config.console_format, config, "stderr"))
            err.setLevel(max(level, int(Severity.WARNING)))
            outputs.append(err)
        else:
            err = ConsoleHandler("stderr")
            err.setFormatter(_formatter(config.console_format, config, "stderr"))
            err.setLevel(level)
            outputs.append(err)
    if config.file:
        handler = make_file_handler(
            config.file,
            rotate=config.rotate,
            max_bytes=config.max_bytes,
            backup_count=config.backup_count,
            when=config.when,
            encoding=config.encoding,
            utc=config.utc,
        )
        if config.file_chain:
            from .integrity import ChainFormatter, chain_key_from_env

            handler.setFormatter(
                ChainFormatter(config.file, key=chain_key_from_env())
            )
        else:
            handler.setFormatter(_formatter(config.file_format, config))
        handler.setLevel(int(Severity[config.file_level or config.level]))
        outputs.append(handler)
    if config.store_capacity > 0:
        store = EventStoreHandler(config.store_capacity, level=base)
        outputs.append(store)
    for handler in outputs:
        _add_filters(handler, config)
    if config.flight_recorder > 0:
        from .recorder import FlightRecorderHandler

        # The flight recorder is on the log file. Without a log file, it
        # is on the console handler for stderr.
        position = None
        for index, handler in enumerate(outputs):
            if isinstance(handler, logging.FileHandler):
                position = index
        if position is None:
            for index, handler in enumerate(outputs):
                if isinstance(handler, ConsoleHandler):
                    position = index
        if position is not None:
            recorder = FlightRecorderHandler(
                outputs[position],
                config.flight_recorder,
                trigger=config.flight_trigger,
                capture_level=config.flight_level,
            )
            recorder.addFilter(ContextFilter())
            if config.capture_locals:
                recorder.addFilter(LocalsFilter())
            outputs[position] = recorder
    return outputs


def configure(
    config: Union[LogConfig, Mapping[str, Any], str, Path, None] = None,
    **options: Any,
) -> LogConfig:
    """Configure the library.

    The function removes the handlers of a previous call. Then it
    installs the handlers, the formatters, the filters and the hooks
    that the configuration selects. It does not remove handlers that
    other code installed.

    Parameters
    ----------
    config
        A :class:`LogConfig`, a dictionary of options, or the path of a
        TOML file or a JSON file. ``None`` selects the default values.
    **options
        Options that replace the values of ``config``.

    Returns
    -------
    LogConfig
        The configuration in use.

    Raises
    ------
    ConfigurationError
        If the configuration is not correct.

    Examples
    --------
    >>> from annunciator import configure, shutdown
    >>> config = configure(level="DEBUG", console=False, install_hooks=False)
    >>> config.level
    'DEBUG'
    >>> shutdown()
    """
    if config is None:
        resolved = LogConfig()
    elif isinstance(config, LogConfig):
        resolved = config
    elif isinstance(config, Mapping):
        resolved = LogConfig.from_dict(config)
    elif isinstance(config, (str, Path)):
        resolved = LogConfig.from_file(config)
    else:
        raise _bad("config", config)
    if options:
        resolved = resolved.replace(**options)

    from . import hooks
    from .logger import get_logger

    with _LOCK:
        shutdown()
        target = logging.getLogger(resolved.logger_name or None)
        outputs = _build_outputs(resolved)
        _STATE.store = next(
            (h for h in outputs if isinstance(h, EventStoreHandler)), None
        )
        levels = [h.level for h in outputs] or [int(Severity[resolved.level])]
        _STATE.previous_level = target.level
        target.setLevel(min(min(levels), int(Severity[resolved.level])))

        if resolved.asynchronous and outputs:
            channel: "queue.Queue[logging.LogRecord]" = queue.Queue(-1)
            front = AsyncQueueHandler(channel)
            if resolved.capture_locals:
                front.addFilter(LocalsFilter())
            listener = logging.handlers.QueueListener(
                channel, *outputs, respect_handler_level=True
            )
            listener.start()
            _STATE.listener = listener
            installed: List[logging.Handler] = [front]
        else:
            installed = list(outputs)
        for handler in installed:
            handler._annunciator_managed = True  # type: ignore[attr-defined]
            target.addHandler(handler)
        _STATE.handlers = installed
        _STATE.outputs = outputs
        _STATE.target = target
        _STATE.config = resolved

        for name, level in resolved.logger_levels.items():
            logging.getLogger(name).setLevel(int(Severity[level]))

        if resolved.install_hooks or resolved.capture_warnings:
            hooks.install_hooks(
                exceptions=resolved.install_hooks,
                threads=resolved.install_hooks,
                unraisable=resolved.install_hooks,
                warnings=resolved.capture_warnings,
            )
            _STATE.hooks_by_config = True

        if not _STATE.atexit_registered:
            atexit.register(shutdown)
            _STATE.atexit_registered = True

    get_logger("annunciator").event(
        "ANN-D-0010",
        level=resolved.level,
        handlers=", ".join(type(h).__name__ for h in outputs) or "none",
    )
    return resolved


def shutdown() -> None:
    """Remove the handlers and the hooks that :func:`configure` installed.

    The function writes all records that are in the queue. Then it
    closes the log file. It is safe to call the function when the
    library is not configured.
    """
    from . import hooks, multiprocess
    from .logger import record_suppressed_summary

    with _LOCK:
        if _STATE.config is not None:
            try:
                multiprocess.stop_listener()
                record_suppressed_summary()
            except Exception:  # noqa: BLE001 - shutdown must not fail
                pass
        if _STATE.hooks_by_config:
            hooks.uninstall_hooks()
            _STATE.hooks_by_config = False
        target = _STATE.target
        if target is not None:
            for handler in _STATE.handlers:
                target.removeHandler(handler)
            if _STATE.previous_level is not None:
                target.setLevel(_STATE.previous_level)
        if _STATE.listener is not None:
            _STATE.listener.stop()
            _STATE.listener = None
        for handler in list(_STATE.handlers) + list(_STATE.outputs):
            try:
                handler.flush()
                handler.close()
            except Exception:  # noqa: BLE001 - shutdown must not fail
                pass
        _STATE.handlers = []
        _STATE.outputs = []
        _STATE.target = None
        _STATE.store = None
        _STATE.config = None
        _STATE.previous_level = None


def is_configured() -> bool:
    """Return ``True`` if :func:`configure` installed the handlers."""
    return _STATE.config is not None


def current_config() -> Optional[LogConfig]:
    """Return the configuration in use, or ``None``."""
    return _STATE.config


def get_store() -> Optional[EventStoreHandler]:
    """Return the event store of the configuration, or ``None``.

    The event store is available when the option ``store_capacity`` is
    more than 0.
    """
    return _STATE.store
