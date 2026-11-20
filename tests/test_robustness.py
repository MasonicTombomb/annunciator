"""Tests of the handling of unusual record and event data."""

import logging

from annunciator.events import Event
from annunciator.filters import CodeFilter


def _record(**attributes):
    record = logging.LogRecord("demo", logging.WARNING, __file__, 1, "text", None, None)
    for name, value in attributes.items():
        setattr(record, name, value)
    return record


def test_code_filter_accepts_code_that_is_not_text():
    record = _record(ann_code=1234)
    assert CodeFilter(include=["12*"]).filter(record)
    assert not CodeFilter(exclude=["12*"]).filter(record)


def test_code_filter_passes_uncoded_record():
    assert CodeFilter(include=["DEMO-*"]).filter(_record())
    assert not CodeFilter(include=["DEMO-*"], pass_uncoded=False).filter(_record())


def test_event_from_dict_ignores_malformed_exception_and_source():
    event = Event.from_dict(
        {"severity": "WARNING", "message": "m", "exception": "text", "source": 5}
    )
    assert event.exception is None
    assert event.source is None
