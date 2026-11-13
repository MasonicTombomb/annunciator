"""annunciator: error, warning and information handling and logging.

The package gives one consistent system for these functions:

* structured log records with severity levels and context data,
* message catalogues with a code, a cause and a remedy for each message,
* coded exceptions and coded warnings,
* decorators and context managers for error handling,
* hooks that record exceptions that no code caught,
* reports and a command-line interface for log files,
* a flight recorder, progress records and stall detection for long runs,
* run manifests and tamper-evident log files,
* safe logs from many processes, soft checks and tools for tests.

The package uses only the Python standard library.

Examples
--------
>>> import annunciator
>>> config = annunciator.configure(console=False, install_hooks=False)
>>> log = annunciator.get_logger("example")
>>> log.info("The run started.", run=17)
>>> annunciator.get_store().events[-1].fields
{'run': 17}
>>> annunciator.shutdown()
"""

from ._version import __version__
from .catalogue import (
    BUILTIN,
    MessageCatalogue,
    MessageDefinition,
    catalogues,
    explain,
    get_catalogue,
    lookup,
    make_code,
    parse_code,
    register_catalogue,
    unregister_catalogue,
)
from .config import (
    LogConfig,
    configure,
    current_config,
    get_store,
    is_configured,
    shutdown,
)
from .context import (
    bind,
    clear_context,
    context,
    get_context,
    new_correlation_id,
    unbind,
)
from .errors import (
    AggregateError,
    CatalogueError,
    CodedError,
    ConfigurationError,
    DataError,
    DependencyError,
    InternalError,
    OperationError,
    OperationTimeoutError,
    ResourceAccessError,
    ResourceError,
    ResourceNotFoundError,
    RetryExhaustedError,
    ValidationError,
)
from .events import Event, ExceptionInfo, SourceLocation
from .checks import (
    check,
    check_finite,
    check_not_empty,
    check_one_of,
    check_range,
    check_type,
)
from .handling import (
    ErrorCollector,
    deprecated,
    guard,
    handle_errors,
    log_calls,
    retry,
    timed,
)
from .hooks import (
    hooks_installed,
    install_asyncio_handler,
    install_hooks,
    uninstall_hooks,
)
from .integrity import verify_chain
from .levels import Severity, register_levels
from .logger import (
    StructuredLogger,
    get_logger,
    record_suppressed_summary,
    reset_occurrences,
    suppressed_counts,
)
from .provenance import Run, collect_manifest, start_run
from .recorder import FlightRecorderHandler
from .report import (
    EventReport,
    RunComparison,
    compare_runs,
    export_csv,
    read_events,
    select_events,
    summarise,
    write_events,
)
from .watch import Progress, Watchdog, track
from .htmlreport import write_html_report
from .warns import (
    CodedWarning,
    ConfigurationWarning,
    DataQualityWarning,
    DeprecatedFeatureWarning,
    PerformanceWarning,
    warn,
)

register_levels()

__all__ = [
    "__version__",
    # levels
    "Severity",
    "register_levels",
    # catalogue
    "BUILTIN",
    "MessageCatalogue",
    "MessageDefinition",
    "catalogues",
    "explain",
    "get_catalogue",
    "lookup",
    "make_code",
    "parse_code",
    "register_catalogue",
    "unregister_catalogue",
    # configuration
    "LogConfig",
    "configure",
    "current_config",
    "get_store",
    "is_configured",
    "shutdown",
    # context
    "bind",
    "clear_context",
    "context",
    "get_context",
    "new_correlation_id",
    "unbind",
    # errors
    "AggregateError",
    "CatalogueError",
    "CodedError",
    "ConfigurationError",
    "DataError",
    "DependencyError",
    "InternalError",
    "OperationError",
    "OperationTimeoutError",
    "ResourceAccessError",
    "ResourceError",
    "ResourceNotFoundError",
    "RetryExhaustedError",
    "ValidationError",
    # warnings
    "CodedWarning",
    "ConfigurationWarning",
    "DataQualityWarning",
    "DeprecatedFeatureWarning",
    "PerformanceWarning",
    "warn",
    # events
    "Event",
    "ExceptionInfo",
    "SourceLocation",
    # loggers
    "StructuredLogger",
    "get_logger",
    # handling
    "ErrorCollector",
    "deprecated",
    "guard",
    "handle_errors",
    "log_calls",
    "retry",
    "timed",
    # hooks
    "hooks_installed",
    "install_asyncio_handler",
    "install_hooks",
    "uninstall_hooks",
    # reports
    "EventReport",
    "export_csv",
    "read_events",
    "select_events",
    "summarise",
    "write_events",
    "RunComparison",
    "compare_runs",
    "write_html_report",
    # long runs
    "FlightRecorderHandler",
    "Progress",
    "Watchdog",
    "track",
    "record_suppressed_summary",
    "reset_occurrences",
    "suppressed_counts",
    # runs and integrity
    "Run",
    "collect_manifest",
    "start_run",
    "verify_chain",
    # checks
    "check",
    "check_finite",
    "check_not_empty",
    "check_one_of",
    "check_range",
    "check_type",
]
