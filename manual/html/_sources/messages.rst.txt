.. index:: messages, problem resolution, troubleshooting, error messages

Messages and problem resolution
===============================

This chapter helps you to correct problems. It has three parts:

* :ref:`how to find the remedy for a message <find-remedy>`,
* :ref:`the reference of all messages of the library <message-reference>`,
* :ref:`the problems that do not show a message code <troubleshooting>`.

.. _find-remedy:

Find the remedy for a message
-----------------------------

.. rubric:: Purpose

To find the probable cause and the remedy of a message that a program
shows.

.. rubric:: Procedure

1. Find the message code in the message. The code is in square brackets,
   for example ``[ANN-E-0003]``.
2. Read the lines ``Cause:`` and ``Remedy:`` below the message, if the
   program shows them.
3. If the program does not show these lines, do this command:

   .. code-block:: console

      annunciator explain ANN-E-0003

4. If the prefix is ``ANN``, you can also find the code in
   :ref:`the message reference <message-reference>` or in the index.
5. If the prefix is different, the message comes from the program that
   uses the library. Refer to the manual of that program.
6. Do the remedy.
7. If the problem continues, do the procedure
   :ref:`Report a problem <report-problem>`.

.. rubric:: Result

You know the probable cause of the message and the corrective action.

How to read a message code
~~~~~~~~~~~~~~~~~~~~~~~~~~

The letter in the middle of the code gives the severity.
:numref:`tab-letter-action` tells you what to do for each letter.

.. list-table:: Severity letters and necessary action
   :name: tab-letter-action
   :widths: 10 20 70
   :header-rows: 1

   * - Letter
     - Severity
     - Action
   * - T, D, I, N
     - ``TRACE`` to ``NOTICE``
     - No action is necessary. The message is information.
   * - W
     - ``WARNING``
     - Read the cause. Make sure that the result is correct.
   * - E
     - ``ERROR``
     - Do the remedy. Then do the operation again.
   * - C
     - ``CRITICAL``
     - Do the remedy. Then start the program again.

.. _message-reference:

Message reference
-----------------

This section gives all messages of the library, in the sequence of their
message numbers. :numref:`tab-number-ranges` gives the number ranges.

.. list-table:: Number ranges of the library messages
   :name: tab-number-ranges
   :widths: 25 75
   :header-rows: 1

   * - Numbers
     - Subject
   * - 0001 to 0099
     - Configuration
   * - 0101 to 0199
     - Message catalogues
   * - 0201 to 0299
     - Hooks: unhandled exceptions and Python warnings
   * - 0301 to 0399
     - Handling tools, progress, stalls and the flight recorder
   * - 0401 to 0499
     - Runs
   * - 0501 to 0599
     - Reports and integrity checks
   * - 0601 to 0699
     - Soft checks

.. annunciator-catalogue:: ANN
   :heading: ~

.. _troubleshooting:

Problems without a message code
-------------------------------

.. list-table:: Problems, probable causes and remedies
   :name: tab-troubleshooting
   :class: longtable
   :widths: 28 32 40
   :header-rows: 1

   * - Problem
     - Probable cause
     - Remedy
   * - The terminal cannot find the command ``annunciator``.
     - The directory of the Python scripts is not in the search path of
       the terminal.
     - Use ``python -m annunciator``. If you use a virtual environment,
       activate it.
   * - Python shows ``ModuleNotFoundError: No module named
       'annunciator'``.
     - The library is not installed in the Python environment that runs
       the program.
     - Do the procedure in :doc:`installation` with the same Python
       environment.
   * - The console shows no events.
     - The program did not call ``configure``, or the option ``level`` is
       too high, or the option ``console`` is false.
     - Call ``configure`` near the start of the program. Decrease
       ``level`` or ``console_level``.
   * - The console shows each event two times.
     - A different handler is installed on the root logger, for example
       by ``logging.basicConfig``.
     - Remove the call of ``logging.basicConfig``. Use only ``configure``.
   * - The log file does not exist.
     - The library makes the file when it writes the first record. No
       record had the necessary severity.
     - Decrease ``level`` or ``file_level``.
   * - The log file does not contain the last events.
     - The option ``asynchronous`` is true and the program stopped
       abnormally.
     - Call ``shutdown`` before the program stops. Set ``asynchronous``
       to false if the problem continues.
   * - The console shows no colour.
     - The output is not a terminal, or the variable ``NO_COLOR`` is set.
     - Set ``console_format`` to ``"colour"``.
   * - The console shows characters such as ``[32m`` in the text.
     - The terminal does not support ANSI colour codes.
     - Set ``console_format`` to ``"plain"``.
   * - A field shows ``[REDACTED]`` but the value is not secret.
     - The field name contains a part that is in ``redact_keys``, for
       example ``token``.
     - Change the field name, or remove the part from ``redact_keys``.
   * - A Python warning is in the log only one time.
     - The standard ``warnings`` module shows the same warning from the
       same line only one time.
     - No action is necessary. To record each occurrence, call
       ``warnings.simplefilter("always")``.
   * - The source position of an event is a line in your own helper
       function.
     - The helper function calls the log method.
     - Give the parameter ``stacklevel=2`` to the log method in the helper
       function.
   * - The summary of ``summarise()`` contains fewer events than the log
       file.
     - The event store is full and removed the oldest events.
     - Increase ``store_capacity``, or make the summary from the log
       file.
   * - The log file contains ``DEBUG`` records but the option ``level`` is
       ``"INFO"``.
     - The flight recorder wrote its kept records after an error. These
       records have the field ``flight_recorder``.
     - No action is necessary. To stop this function, set
       ``flight_recorder`` to 0.
   * - The message of ``once`` does not occur in a second run of the same
       process.
     - The library keeps the state of ``once`` until the process stops.
     - Use ``start_run`` for each run, or call ``reset_occurrences``.
   * - The command ``verify`` fails for a file that nobody changed.
     - The program used a key and the command does not have the same key.
       A different cause is an incomplete last line after an abnormal
       stop.
     - Set ``ANNUNCIATOR_CHAIN_KEY`` to the key of the run. Examine the
       last line of the file.
   * - The records of worker processes are not in the log file.
     - The worker processes did not call ``init_worker``, or the program
       stopped before ``stop_listener``.
     - Do the procedure in :doc:`proc_robust`.
   * - A watchdog records ``ANN-W-0332`` but the operation is in
       progress.
     - The code does not call ``beat`` or ``update`` frequently, or the
       limit is too short.
     - Call ``beat`` in the inner loop, or increase the limit.
   * - A TOML file cannot be read on Python 3.9 or 3.10. The reason
       contains ``tomli``.
     - The package ``tomli`` is not installed.
     - Install the extra ``toml``. Refer to :doc:`installation`.

.. _report-problem:

Report a problem
----------------

.. rubric:: Purpose

To give the necessary data to the person who supplies the software.

.. rubric:: Procedure

1. Set the option ``level`` to ``"DEBUG"`` and the option ``file_format``
   to ``"json"``.
2. Do the operation that causes the problem again.
3. Collect these items:

   * the log file,
   * the output of ``annunciator --version``,
   * the output of ``python --version``,
   * the name and the version of the operating system,
   * the steps that cause the problem.

   .. caution::

      Read the log file before you send it. Make sure that it contains no
      secret data.

4. Send the items to the person who supplied the software to you.

.. rubric:: Result

The supplier has the data that are necessary to find the cause.
