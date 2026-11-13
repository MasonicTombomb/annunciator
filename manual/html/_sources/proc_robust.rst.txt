.. index:: multiprocessing; procedure, local variables; procedure,
   soft check; procedure

Make the records robust
=======================

.. rubric:: Purpose

To get correct log files from many processes and to keep the data of a
failure. Also to examine data without much code.

Write one log from many processes
---------------------------------

.. caution::

   Do not let many processes write to the same log file directly. The
   lines can mix and the rotation can remove records.

.. rubric:: Procedure

1. In the primary process, call ``configure``.
2. Call ``start_listener`` to get the queue.
3. Start the worker processes with ``init_worker`` as the initializer and
   the queue as its argument.
4. After the worker processes stop, call ``stop_listener``:

   .. code-block:: python
      :caption: One log file for a pool of processes
      :name: ex-multiprocess

      import multiprocessing

      from annunciator import configure, get_logger
      from annunciator.multiprocess import init_worker, start_listener, stop_listener

      def simulate(case):
          log = get_logger("worker")
          log.info("The case started.", case=case)
          return run_case(case)

      if __name__ == "__main__":
          configure(file="logs/run.jsonl", file_format="json")
          queue = start_listener()
          with multiprocessing.Pool(8, init_worker, (queue,)) as pool:
              results = pool.map(simulate, cases)
          stop_listener()

.. rubric:: Result

Only the primary process writes the log file. Each event contains the
identifier of the process that recorded it. The filters, the event store
and the flight recorder of the primary process apply to all events.

.. note::

   On Windows, put the code of the primary process below the line
   ``if __name__ == "__main__":``. This is a rule of the standard
   ``multiprocessing`` module.

Keep the local variables of a failure
-------------------------------------

Use this procedure for runs that are too long to do again with a debugger.

.. rubric:: Procedure

1. Set the option ``capture_locals`` to true:

   .. code-block:: python

      configure(file="logs/run.jsonl", file_format="json", capture_locals=True)

2. Record exceptions with ``report``, ``exception`` or a handling tool.

.. rubric:: Result

Each event with a traceback contains the local variables of the last two
functions of the traceback. In the plain text format, the variables are
below the traceback:

.. code-block:: text

       IndexError: list index out of range
       Fingerprint: 46c1ff9f2e2a
       Local variables of channel_counts (spectrum.py:88):
           password = [REDACTED]
           index = 8192
           counts = [0, 3, 1, 0, 2, ...]

The library keeps a maximum of 200 characters for each value.

.. caution::

   Local variables can contain secret data. The redaction filter replaces
   the values of variables that have secret names. It does not examine
   the values of other variables. Read a log file before you send it.

Examine data with soft checks
-----------------------------

A soft check examines a condition on data and gives a coded message when
the condition is not true. You select if the check raises an error or
only records a warning.

.. rubric:: Procedure

1. Select the check in :numref:`tab-checks`.
2. Call the check with the value and a name for the value.
3. Select the action with the parameter ``on_fail``.
   :numref:`tab-onfail` gives the effect.

   .. code-block:: python
      :caption: Soft checks
      :name: ex-checks

      from annunciator import check, check_finite, check_not_empty, check_range

      check_not_empty(spectrum, name="spectrum")
      check_range(live_time, 0, None, name="live_time", inclusive=False)
      check_finite(efficiency, name="efficiency", on_fail="warn")
      if not check_range(dead_time, 0, 30, name="dead_time", on_fail="log"):
          apply_dead_time_correction()
      check(len(energy) == len(counts), name="axis length",
            energy=len(energy), counts=len(counts))

.. list-table:: Soft checks
   :name: tab-checks
   :widths: 25 45 30
   :header-rows: 1

   * - Function
     - Condition that the check examines
     - Codes
   * - ``check_range``
     - A number is between a minimum and a maximum.
     - ``ANN-E-0601``, ``ANN-W-0611``
   * - ``check_finite``
     - The data contain no NaN and no infinite values.
     - ``ANN-E-0602``, ``ANN-W-0612``
   * - ``check_type``
     - A value has a permitted type.
     - ``ANN-E-0603``, ``ANN-W-0613``
   * - ``check_not_empty``
     - A sequence, a text or a data set contains items.
     - ``ANN-E-0604``, ``ANN-W-0614``
   * - ``check_one_of``
     - A value is in a list of permitted values.
     - ``ANN-E-0605``, ``ANN-W-0615``
   * - ``check``
     - A condition that you supply is true.
     - ``ANN-E-0606``, ``ANN-W-0616``

.. list-table:: Values of the parameter ``on_fail``
   :name: tab-onfail
   :widths: 20 80
   :header-rows: 1

   * - Value
     - Effect when the condition is not true
   * - ``"raise"``
     - The check raises ``ValidationError`` with the ``E`` code. This is
       the default.
   * - ``"warn"``
     - The check issues ``DataQualityWarning`` with the ``W`` code. The
       program continues. Warning filters apply.
   * - ``"log"``
     - The check records a ``WARNING`` event with the ``W`` code. The
       program continues.

.. rubric:: Result

Each check returns ``True`` if the condition is true. If the condition is
not true, the check does the selected action and returns ``False``.

.. note::

   To use a message of your own catalogue, give the parameter ``code``.
