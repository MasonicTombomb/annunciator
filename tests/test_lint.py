"""Tests of the static check of message codes (``annunciator.lint``)."""

import inspect
from pathlib import Path

import pytest

import annunciator
from annunciator import MessageCatalogue, unregister_catalogue
from annunciator.lint import lint_paths

SOURCE = Path(inspect.getfile(annunciator)).parent

#: Field names that are parameters of some functions with a ``code=``
#: keyword, but not of ``StructuredLogger.event``.
FIELD_NAMES = (
    "category", "cause", "context", "key", "logger", "operation", "remedy",
    "severity", "stack_info",
)


@pytest.fixture(autouse=True)
def demo_catalogue():
    catalogue = MessageCatalogue("DEMO", "lint tests", replace=True)
    catalogue.define(100, "E", "The operation '{operation}' failed for '{item}'.")
    catalogue.define(101, "W", "The value {value} is too high.")
    catalogue.define(102, "E", "The key '{key}' is not correct.")
    for number, name in enumerate(FIELD_NAMES, start=1):
        catalogue.define(number, "W", f"The {name} is {{{name}}}.")
    yield catalogue
    unregister_catalogue("DEMO")


def lint_source(tmp_path, *lines):
    path = tmp_path / "demo_app.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    findings = lint_paths([path], prefixes=["ANN", "DEMO"], unused=False)
    return [(f.line, f.kind, f.code, f.detail) for f in findings]


@pytest.mark.parametrize(
    "call",
    [
        'log.event("ANN-E-0304", count=2, operation="import files")',
        'log.event("ANN-W-0205", category="UserWarning", text="hello")',
        'log.event("ANN-I-0320", count=3, key="demo")',
        'log.event("ANN-I-0308", operation="fit", elapsed="1.0")',
        'log.event("DEMO-E-0100", operation="load", item="a.csv")',
        'log.event(code="DEMO-E-0100", operation="load", item="a.csv")',
    ]
    + [
        f'log.event("DEMO-W-{number:04d}", {name}="x")'
        for number, name in enumerate(FIELD_NAMES, start=1)
    ],
)
def test_event_with_all_fields_is_clean(tmp_path, call):
    assert lint_source(tmp_path, call) == []


def test_event_without_field_is_reported(tmp_path):
    assert lint_source(tmp_path, 'log.event("DEMO-E-0100", item="a.csv")') == [
        (1, "missing-field", "DEMO-E-0100", "no value for: operation")
    ]


def test_event_parameter_is_not_a_field(tmp_path):
    findings = lint_source(
        tmp_path, 'log.event("DEMO-E-0100", item="a.csv", strict=True)'
    )
    assert [f[3] for f in findings] == ["no value for: operation"]


@pytest.mark.parametrize(
    "call",
    [
        'OperationError(code="DEMO-E-0100", operation="load", item="a.csv")',
        'errors.OperationError(code="DEMO-E-0100", operation="load", item="a.csv")',
        'ValidationError(code="DEMO-E-0102", key="k")',
        'DataQualityWarning(code="DEMO-W-0004", key="k")',
        'OperationError("own text", code="DEMO-E-0100")',
        'OperationError(message="own text", code="DEMO-E-0100")',
        'AggregateError(code="ANN-E-0304", errors=[], operation="import")',
    ],
)
def test_coded_class_with_all_fields_is_clean(tmp_path, call):
    assert lint_source(tmp_path, call) == []


def test_coded_class_parameter_is_not_a_field(tmp_path):
    findings = lint_source(
        tmp_path, 'OperationError(code="DEMO-E-0100", item="a", cause="x")'
    )
    assert [f[3] for f in findings] == ["no value for: operation"]


def test_coded_class_none_message_is_examined(tmp_path):
    findings = lint_source(tmp_path, 'OperationError(None, code="DEMO-E-0100")')
    assert [f[3] for f in findings] == ["no value for: operation, item"]


def test_warn_none_without_field_is_reported(tmp_path):
    assert lint_source(
        tmp_path, 'warn(None, DataQualityWarning, code="DEMO-W-0101")'
    ) == [(1, "missing-field", "DEMO-W-0101", "no value for: value")]


def test_warn_with_message_text_is_clean(tmp_path):
    assert lint_source(
        tmp_path, 'warn("text", DataQualityWarning, code="DEMO-W-0101")'
    ) == []


def test_warn_with_field_is_clean(tmp_path):
    assert lint_source(
        tmp_path,
        'annunciator.warn(None, DataQualityWarning, code="DEMO-W-0101", value=3)',
    ) == []


def test_double_star_fields_are_skipped(tmp_path):
    assert lint_source(tmp_path, 'log.event("DEMO-E-0100", **fields)') == []


def test_own_source_is_clean():
    assert lint_paths([SOURCE], prefixes=["ANN"], unused=False) == []
