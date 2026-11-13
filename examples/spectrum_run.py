"""Complete example: a simulated gamma spectrum run.

Run the example with ``python examples/spectrum_run.py``. It writes the
events to the console and to the file ``logs/spectrum_run.jsonl``. Then
examine the file with these commands::

    annunciator report logs/spectrum_run.jsonl --html report.html
    annunciator verify logs/spectrum_run.jsonl
"""

from __future__ import annotations

import random
import sys

from annunciator import (
    CodedError,
    DataQualityWarning,
    ErrorCollector,
    MessageCatalogue,
    ResourceError,
    configure,
    context,
    check_not_empty,
    get_logger,
    handle_errors,
    retry,
    start_run,
    summarise,
    timed,
    track,
    warn,
)

# -- Message catalogue -------------------------------------------------------

SPEC = MessageCatalogue("SPEC", "Messages of the spectrum example", replace=True)
SPEC.define(
    1, "E", "The detector '{name}' does not answer.",
    cause="The detector has no power or the cable is not connected.",
    remedy="Make sure that the detector has power. Examine the cable.",
)
SPEC.define(
    2, "W", "The dead time is {dead_time} %.",
    cause="The count rate is too high for the detector.",
    remedy="Increase the distance between the source and the detector.",
)
SPEC.define(3, "I", "The run '{run}' completed. Live time: {live_time} s.")
SPEC.define(
    4, "E", "The spectrum of the sample '{sample}' has no counts.",
    cause="The shutter was closed or the sample position was empty.",
    remedy="Examine the sample position. Do the measurement again.",
)


class DetectorError(ResourceError):
    """The detector does not operate."""

    default_code = "SPEC-E-0001"


log = get_logger("spectrum_run")

# -- Simulated hardware ------------------------------------------------------

_state = {"connect_calls": 0}


@retry(ConnectionError, attempts=3, delay=0.05)
def connect(name: str) -> str:
    """Connect to the detector. The first attempt fails."""
    _state["connect_calls"] += 1
    if _state["connect_calls"] < 2:
        raise ConnectionError("The port is busy")
    return name


@handle_errors(ZeroDivisionError, reraise=False, default=float("nan"))
def peak_ratio(a: int, b: int) -> float:
    """Return the ratio of two peak areas."""
    return a / b


def acquire(sample: str, live_time: int) -> list:
    """Return a simulated spectrum."""
    if sample == "EMPTY":
        raise CodedError(code="SPEC-E-0004", sample=sample)
    rng = random.Random(sample)
    dead_time = rng.randint(5, 45)
    if dead_time > 30:
        warn(code="SPEC-W-0002", category=DataQualityWarning,
             stacklevel=2, dead_time=dead_time)
    return [rng.randint(0, 500) for _ in range(64)]


# -- Program -----------------------------------------------------------------

def main() -> int:
    configure(
        level="DEBUG",
        console_level="INFO",
        file="logs/spectrum_run.jsonl",
        file_format="json",
        file_chain=True,
        flight_recorder=200,
    )
    try:
        detector = connect("HPGe-2")
    except CodedError as error:
        log.report(error)
        print(error.describe(), file=sys.stderr)
        return error.exit_code

    samples = ("CeO2-01", "CeO2-02", "EMPTY", "CeO2-04")
    collector = ErrorCollector("measure samples", logger=log)
    with start_run("R-17", seed=17, git=False, live_time=600), \
            context(run="R-17", detector=detector):
        for sample in track(samples, "measure samples", logger=log, interval=0.0):
            with collector.catch(CodedError, sample=sample):
                with timed("acquire", logger=log, sample=sample):
                    spectrum = acquire(sample, live_time=600)
                check_not_empty(spectrum, name="spectrum")
                log.info("The spectrum is complete.", sample=sample,
                         counts=sum(spectrum))
                log.debug("Ratio of the first two channels: %s",
                          peak_ratio(spectrum[0], spectrum[1]))
        log.event("SPEC-I-0003", run="R-17", live_time=600)

    report = summarise()
    print()
    print(report.to_text())
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
