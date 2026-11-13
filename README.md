# annunciator

Error, warning and information handling and logging for Python.

`annunciator` uses only the Python standard library. It gives you:

- structured log records with seven severity levels and context data,
- message catalogues: each message has a code, a cause and a remedy,
- coded exceptions and coded warnings,
- decorators and context managers for error handling (`handle_errors`,
  `guard`, `retry`, `ErrorCollector`, `timed`, `log_calls`, `deprecated`),
- hooks that record exceptions that no code caught,
- plain text, colour and JSON Lines output, with file rotation,
- redaction of secret data, a duplicate filter and a rate limit,
- reports, CSV export and a command-line interface for log files,
- a Sphinx directive that writes your message reference,
- for long runs: a flight recorder, `once`/`every`/`throttle`, progress
  records, stall detection and failure fingerprints,
- for evidence: run manifests, tamper-evident log files (`annunciator
  verify`) and run comparison (`annunciator diff`),
- for robust operation: one log writer for many processes, local variables
  in tracebacks and soft checks,
- for development: `annunciator lint`, a pytest fixture and an HTML report.

## Install

Into any Python environment (venv, conda, mamba, pyenv, system):

```console
python -m pip install annunciator
```

From GitHub (latest `main`, or a fixed tag):

```console
python -m pip install "git+https://github.com/MasonicTombomb/annunciator.git"
python -m pip install "git+https://github.com/MasonicTombomb/annunciator.git@v1.1.1"
```

With uv: `uv pip install annunciator`. In a conda environment, `pip install`
as above works; a native conda package is also built for each release
(`conda install -c MasonicTombomb annunciator` when it is uploaded to
anaconda.org).

From a local clone: `python -m pip install .`

Python 3.9 or later is necessary. On Python 3.9 and 3.10, install the extra
`toml` to read TOML files: `python -m pip install "annunciator[toml]"`.

## Release

1. Set `__version__` in `src/annunciator/_version.py` and add an entry to
   `CHANGELOG.md`.
2. Commit, then tag and push: `git tag v1.2.0 && git push origin main v1.2.0`.

The workflow `.github/workflows/release.yml` builds the sdist and wheel,
tests them on Linux, Windows and macOS, publishes to PyPI, creates a GitHub
release with the files attached and builds a conda package.

## Quick start

```python
from annunciator import MessageCatalogue, CodedError, configure, get_logger

configure(level="INFO", file="logs/run.jsonl", file_format="json")
log = get_logger(__name__)

APP = MessageCatalogue("APP", "Application messages")
APP.define(1, "E", "The detector '{name}' does not answer.",
           cause="The detector has no power or the cable is not connected.",
           remedy="Make sure that the detector has power. Examine the cable.")

log.info("The measurement started.", sample="CeO2-04", live_time=600)
log.event("APP-E-0001", name="HPGe-2")
raise CodedError(code="APP-E-0001", name="HPGe-2")
```

## Documentation

The built user manual (document ANN-UM-001) is in the directory `manual`
(PDF and HTML). Its source files are in the directory `docs`. Its
structure follows ISO/IEC/IEEE 26514:2022. Its text follows the writing rules
of ASD-STE100 Issue 9.

```console
python -m pip install ".[docs]"
sphinx-build -b html docs docs/_build/html
sphinx-build -M latexpdf docs docs/_build
python tools/ste_check.py docs
```

## Licence

MIT. Refer to the file `LICENSE`.
