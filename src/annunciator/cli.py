"""Command-line interface.

Start the interface with the command ``annunciator`` or with
``python -m annunciator``. The user manual gives the full data for each
command.

The exit status is 0 when a command completes. The user manual gives the
other values.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import List, Optional, Sequence

from ._version import __version__
from .catalogue import MessageCatalogue, catalogues, explain
from .config import LogConfig
from .errors import CodedError
from .formatters import PlainFormatter
from .levels import Severity
from .report import EventReport, compare_runs, export_csv, read_events, select_events

__all__ = ["main", "build_parser"]


def build_parser() -> argparse.ArgumentParser:
    """Make the argument parser of the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="annunciator",
        description="Tools for message catalogues and JSON Lines log files.",
    )
    parser.add_argument(
        "--version", action="version", version=f"annunciator {__version__}"
    )
    parser.add_argument(
        "-i", "--import", dest="imports", action="append", default=[],
        metavar="MODULE",
        help="import a module that registers message catalogues "
             "(you can give this option more than one time)",
    )
    parser.add_argument(
        "-c", "--catalogue-file", dest="files", action="append", default=[],
        metavar="FILE",
        help="read a message catalogue from a JSON file or a TOML file",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    cat = commands.add_parser(
        "catalogue", help="show the messages of the registered catalogues"
    )
    cat.add_argument("--prefix", help="show only the catalogue with this prefix")
    cat.add_argument("--min-severity", help="show only this severity or higher")
    cat.add_argument("--search", help="show only the messages that contain this text")
    cat.add_argument(
        "--format", choices=("text", "json", "rst"), default="text",
        help="output format (default: text)",
    )

    exp = commands.add_parser("explain", help="show the full definition of a message")
    exp.add_argument("code", help="message code, for example ANN-E-0001")

    rep = commands.add_parser("report", help="summarise a JSON Lines log file")
    rep.add_argument("path", help="path of the log file")
    rep.add_argument("--json", action="store_true", help="write the report as JSON")
    rep.add_argument("--html", metavar="FILE",
                     help="write an HTML report of the selected events")
    rep.add_argument("--title", default="Run report",
                     help="title of the HTML report")
    _add_selection(rep)

    view = commands.add_parser("view", help="show the events of a JSON Lines log file")
    view.add_argument("path", help="path of the log file")
    view.add_argument("--no-help", action="store_true",
                      help="do not show the cause and the remedy")
    view.add_argument("--csv", metavar="FILE", help="write the events to a CSV file")
    _add_selection(view)

    chk = commands.add_parser("check-config", help="examine a configuration file")
    chk.add_argument("path", help="path of the TOML file or the JSON file")

    ver = commands.add_parser(
        "verify", help="examine the integrity data of a JSON Lines log file"
    )
    ver.add_argument("path", help="path of the log file")
    ver.add_argument("--key-env", default="ANNUNCIATOR_CHAIN_KEY", metavar="NAME",
                     help="environment variable that contains the key "
                          "(default: ANNUNCIATOR_CHAIN_KEY)")
    ver.add_argument("--expected-start", metavar="HASH",
                     help="last hash of the older file, after a rotation")

    dif = commands.add_parser("diff", help="compare the events of two log files")
    dif.add_argument("first", help="log file of the reference run")
    dif.add_argument("second", help="log file of the run to examine")
    dif.add_argument("--json", action="store_true",
                     help="write the comparison as JSON")

    lnt = commands.add_parser(
        "lint", help="examine the message codes in Python source files"
    )
    lnt.add_argument("paths", nargs="+", help="Python files or directories")
    lnt.add_argument("--prefix", action="append", default=[],
                     help="examine only this catalogue prefix "
                          "(you can give this option more than one time)")
    lnt.add_argument("--no-unused", action="store_true",
                     help="do not show the codes that the source does not use")
    lnt.add_argument("--strict", action="store_true",
                     help="give the exit status 1 for unused codes also")

    commands.add_parser("demo", help="show an example of each severity")
    return parser


def _add_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-severity", help="select this severity or higher")
    parser.add_argument("--code", help="select codes that agree with this pattern")
    parser.add_argument("--logger", help="select loggers that agree with this pattern")
    parser.add_argument("--text", help="select messages that contain this text")
    parser.add_argument("--fingerprint",
                        help="select events of the failure with this fingerprint")


def _selected(args: argparse.Namespace):
    return select_events(
        read_events(args.path),
        minimum=args.min_severity,
        code=args.code,
        logger=args.logger,
        text=args.text,
        fingerprint=args.fingerprint,
    )


def _catalogue_rst(items: Sequence[MessageCatalogue], selection: dict) -> str:
    lines: List[str] = []
    for catalogue in items:
        lines += [catalogue.title, "=" * len(catalogue.title), ""]
        for item in catalogue.select(**selection):
            lines += [item.code, "-" * len(item.code), ""]
            lines += [f":Severity: {item.severity.name}"]
            lines += [f":Message: {item.text}"]
            if item.cause:
                lines += [f":Cause: {item.cause}"]
            if item.remedy:
                lines += [f":Remedy: {item.remedy}"]
            lines.append("")
    return "\n".join(lines)


def _cmd_catalogue(args: argparse.Namespace) -> int:
    items = [
        item for item in catalogues()
        if args.prefix is None or item.prefix == args.prefix
    ]
    selection = {"minimum": args.min_severity, "text": args.search}
    if args.format == "json":
        data = []
        for catalogue in items:
            entry = catalogue.to_dict()
            entry["messages"] = [
                item.to_dict() for item in catalogue.select(**selection)
            ]
            data.append(entry)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.format == "rst":
        print(_catalogue_rst(items, selection))
    else:
        for catalogue in items:
            print(f"{catalogue.prefix}: {catalogue.title}")
            for item in catalogue.select(**selection):
                print(f"  {item.code}  {item.text}")
    return 0


def _cmd_demo() -> int:
    from . import configure, get_logger, shutdown

    configure(level="TRACE", install_hooks=False, capture_warnings=False)
    log = get_logger("annunciator.demo")
    try:
        for member in Severity:
            log.log(member, "This is an example of the severity %s.", member.name,
                    value=int(member))
        log.event("ANN-E-0001", option="colour_mode")
    finally:
        shutdown()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Do one command of the command-line interface.

    Parameters
    ----------
    argv
        The arguments. The default is ``sys.argv[1:]``.

    Returns
    -------
    int
        The exit status.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 64 if exc.code not in (0, None) else 0
    if args.command is None:
        parser.print_help()
        return 64
    try:
        for name in args.imports:
            importlib.import_module(name)
        for path in args.files:
            MessageCatalogue.load(path, replace=True)

        if args.command == "catalogue":
            return _cmd_catalogue(args)
        if args.command == "explain":
            print(explain(args.code))
            return 0
        if args.command == "report":
            selected = list(_selected(args))
            report = EventReport.from_events(selected)
            if args.html:
                from .htmlreport import write_html_report

                write_html_report(selected, args.html, title=args.title)
                print(f"The HTML report is in the file {args.html}")
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(report.to_text())
            return report.exit_code()
        if args.command == "view":
            if args.csv:
                number = export_csv(_selected(args), args.csv)
                print(f"{number} events written to {args.csv}")
                return 0
            formatter = PlainFormatter(show_help=not args.no_help)
            for event in _selected(args):
                print(formatter.format_event(event))
            return 0
        if args.command == "check-config":
            config = LogConfig.from_file(args.path)
            print(f"The configuration file is correct: {args.path}")
            for key, value in config.to_dict().items():
                print(f"  {key} = {value!r}")
            return 0
        if args.command == "verify":
            from .integrity import chain_key_from_env, verify_chain

            result = verify_chain(
                args.path,
                key=chain_key_from_env(args.key_env),
                expected_start=args.expected_start,
            )
            print(result.to_text())
            return 0 if result.ok else 1
        if args.command == "diff":
            comparison = compare_runs(args.first, args.second)
            if args.json:
                print(json.dumps(comparison.to_dict(), indent=2))
            else:
                print(comparison.to_text())
            return 1 if comparison.regression else 0
        if args.command == "lint":
            from .lint import lint_paths

            findings = lint_paths(
                args.paths, prefixes=args.prefix or None,
                unused=not args.no_unused,
            )
            for finding in findings:
                print(finding.to_text())
            errors = sum(1 for finding in findings if finding.is_error)
            print(f"{len(findings)} findings, {errors} errors")
            if errors or (args.strict and findings):
                return 1
            return 0
        if args.command == "demo":
            return _cmd_demo()
    except CodedError as error:
        print(error.describe(), file=sys.stderr)
        return error.exit_code
    except (ImportError, OSError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 66
    return 64  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
