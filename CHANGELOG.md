# Change record

## 1.1.4 (2026-11-20)

Fixed:

- `CodeFilter` accepts a message code that is not text (for example an
  integer). Before, the filter raised `TypeError` in the logging call.
- `Event.from_dict` ignores an `exception` or `source` entry that is not
  a mapping. Before, a malformed event record raised `AttributeError`.
- Type fixes in `events`, `handlers`, `hooks`, `testing`, `formatters` and
  `sphinxext`. The PyCharm inspections give no warnings or errors for
  these modules.

Added:

- Tests of unusual record and event data (`tests/test_robustness.py`).

## 1.1.3 (2026-11-19)

Fixed:

- `annunciator lint` no longer reports `missing-field` for replacement
  fields named like a parameter of a different function (for example
  `operation`, `category` or `key` in `log.event(...)`). The check now uses
  the parameters of the called function: `event`, `warn`, a coded error or
  warning class, or else the parameters of all functions that take `code=`.
  The lint of the annunciator source code now gives no findings.
- `annunciator lint` now examines the fields of `warn(None, ...)` and of
  calls with `message=None`. `None` is not a message text.
- `annunciator lint`: type fixes and removal of an unused variable.

Added:

- Tests of `annunciator lint` (`tests/test_lint.py`) and the optional
  dependency group `test` (`pip install -e .[test]`).
- `sphinx_rtd_theme` in the optional dependency group `docs`.

## 1.1.2 (2026-11-13)

Changed:

- The conda package gets its version from `src/annunciator/_version.py`.
  Release 1.1.1 has no conda package.
- The release workflow uses Node 24 versions of the GitHub actions.

## 1.1.1 (2026-11-13)

Changed:

- The HTML report has the style of a printed industrial report: a title
  block, numbered sections, ruled tables, a fixed-width font and no colour.
  It adds a summary by message code, event numbers, `EXPAND ALL` and `PRINT`.
- User manual ANN-UM-001, Issue 3.

## 1.1.0 (2026-11-12)

Added:

- Flight recorder: the options `flight_recorder`, `flight_level` and
  `flight_trigger`.
- The log methods `once`, `every` and `throttle`, with a summary of rejected
  records (`ANN-I-0320`).
- `Progress`, `track` and `Watchdog` for progress records and stall detection.
- Failure fingerprints in events and in reports.
- `start_run` and `Run`: run manifest, run result and exit status.
- Tamper-evident log files: the option `file_chain`, `verify_chain` and the
  command `annunciator verify`.
- `compare_runs` and the command `annunciator diff`.
- `annunciator.multiprocess`: one log writer for many processes.
- The option `capture_locals`: local variables in tracebacks, with redaction.
- Soft checks: `check`, `check_range`, `check_finite`, `check_type`,
  `check_not_empty`, `check_one_of`.
- `annunciator lint`: static check of message codes in source code.
- `annunciator.testing`: `capture_events` and the pytest fixture
  `annunciator_events`.
- `write_html_report` and the option `--html` of the command `report`.
- The selection option `--fingerprint`.
- User manual ANN-UM-001, Issue 2.

Changed:

- Plain text shows a maximum of 120 characters for each field value.

## 1.0.0 (2026-11-12)

- First release.
