.. index:: flight recorder; procedure, repeated messages, progress; procedure,
   watchdog, stall, fingerprint; procedure

Monitor a long run
==================

.. rubric:: Purpose

To get the necessary information from a run that operates for hours,
without a log that is too large to read.

.. rubric:: Before you start

Configure the library. Refer to :doc:`proc_configure`. Then select the
tool in :numref:`tab-longrun-choice`.

.. list-table:: Selection of the tool for a long run
   :name: tab-longrun-choice
   :widths: 55 45
   :header-rows: 1

   * - Task
     - Tool
   * - Get the detailed records only when a failure occurs
     - Flight recorder
   * - Record a message in a loop without thousands of equal lines
     - ``once``, ``every``, ``throttle``
   * - Show that a long operation continues, with the remaining time
     - ``Progress``, ``track``
   * - Know when an operation stopped without an error
     - ``Watchdog``
   * - Count how many different failures occurred
     - Fingerprints

Keep detailed records for failures only
---------------------------------------

The flight recorder keeps the last detailed records in memory.
:numref:`fig-recorder` shows its operation. The log file gets the detailed
records only when an event of the trigger severity occurs.

.. figure:: figures/recorder.*
   :name: fig-recorder
   :width: 90%
   :alt: Decision diagram. A record below the file level stays in memory.
         A record at the trigger severity causes the kept records to go to
         the log file first.

   Operation of the flight recorder

.. rubric:: Procedure

1. Set the option ``level`` or ``file_level`` to the severity for a normal
   run, for example ``"INFO"``.
2. Set the option ``flight_recorder`` to the number of records to keep:

   .. code-block:: python
      :caption: Configuration of the flight recorder
      :name: ex-recorder

      from annunciator import configure

      configure(
          level="INFO",
          file="logs/run.jsonl",
          file_format="json",
          flight_recorder=500,
          flight_level="DEBUG",
          flight_trigger="ERROR",
      )

3. Record detailed data with ``log.debug`` in your code, as usual.

.. rubric:: Result

In a run without errors, the log file contains ``INFO`` and higher. When an
``ERROR`` occurs, the file first gets the code ``ANN-I-0340``. Then it gets
a maximum of 500 ``DEBUG`` records that came before the error. Each of
these records has the field ``flight_recorder``.

.. note::

   The kept records have their initial times. Thus the times in the file
   are not always in sequence after the flight recorder wrote its records.

.. caution::

   If the program stops abnormally without an event of the trigger
   severity, the kept records are lost. An example is a loss of power.

Record repeated messages
------------------------

.. rubric:: Procedure

1. For a message that the user must see only one time, use ``once``:

   .. code-block:: python

      log.once("WARNING", "No calibration file. The default applies.")

2. For a message in a loop, use ``every`` with the number of calls
   between two records:

   .. code-block:: python

      for index, particle in enumerate(particles):
          log.every(1000, "INFO", "The classification continues.", index=index)

3. For a message that can occur at a high rate, use ``throttle`` with a
   time in seconds:

   .. code-block:: python

      log.throttle(30.0, "WARNING", "The buffer is almost full.", fill=fill)

.. rubric:: Result

``once`` records the first call. ``every`` records calls 1, 1001, 2001 and
so on, with the field ``occurrence``. ``throttle`` records a maximum of one
message in 30 s, with the field ``suppressed``.

At the end of the run, the library records ``ANN-I-0320`` for each message
that has rejected records. The event gives the number of rejected records.

.. note::

   The library identifies a message by the logger name and the message
   text. If the text changes with each call, give the parameter ``key``.

Record the progress of an operation
-----------------------------------

.. rubric:: Procedure

1. If the operation is a loop, put ``track`` around the items:

   .. code-block:: python
      :caption: Progress of a loop
      :name: ex-track

      from annunciator import track

      for image in track(images, "classify images", interval=30.0):
          classify(image)

2. If the operation is not a simple loop, use ``Progress`` and call
   ``update``:

   .. code-block:: python

      from annunciator import Progress

      with Progress("simulate histories", total=1_000_000, interval=60.0) as progress:
          while not simulation.done:
              progress.update(simulation.step())

.. rubric:: Result

The log contains ``ANN-I-0330`` a maximum of one time in each interval:

.. code-block:: text

   INFO  [ANN-I-0330] Progress of 'classify images': 1200 of 4800 (25.0 %). Rate: 9.87 per second. Time to completion: 365 s.

At the end, the log contains ``ANN-I-0331`` with the number of items and
the duration.

Find an operation that stopped
------------------------------

Use this procedure for an operation that can stop without an exception. An
example is a device that does not answer.

.. rubric:: Procedure

1. If you use ``track`` or ``Progress``, give the parameter
   ``stall_after`` with a time in seconds:

   .. code-block:: python

      for image in track(images, "acquire images", stall_after=120.0):
          acquire(image)

2. If you do not use these tools, make a ``Watchdog`` and call ``beat``
   each time the operation makes progress:

   .. code-block:: python
      :caption: Stall detection
      :name: ex-watchdog

      from annunciator import Watchdog

      with Watchdog(120.0, "acquisition") as watchdog:
          while detector.is_acquiring():
              read_block(detector)
              watchdog.beat()

.. rubric:: Result

If the operation makes no progress for 120 s, the log contains
``ANN-W-0332``. The warning occurs again after each subsequent 120 s. When
the operation continues, the log contains ``ANN-I-0333``.

.. note::

   The watchdog only records the stall. It does not stop the operation. To
   do an action, give a function in the parameter ``on_stall``.

Count the different failures
----------------------------

The library gives a fingerprint to each recorded exception. Two exceptions
have the same fingerprint if they have the same class and the same sequence
of functions in the traceback.

.. rubric:: Procedure

1. Record exceptions with ``report``, ``exception`` or a handling tool.
   The library then adds the fingerprint automatically.
2. Make a summary of the log. Refer to :doc:`proc_reports`.

.. rubric:: Result

The summary contains the section ``Distinct failures``:

.. code-block:: text

   Distinct failures: 2
     46c1ff9f2e2a   3120 x  IndexError: list index out of range
     7e04fdba7321      1 x  ZeroDivisionError: division by zero

Thus you know that 3121 error records come from only two defects. To see
the events of one failure, select the fingerprint:

.. code-block:: console

   annunciator view logs/run.jsonl --fingerprint 46c1ff9f2e2a
