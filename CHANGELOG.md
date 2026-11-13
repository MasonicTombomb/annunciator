# Change record

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
