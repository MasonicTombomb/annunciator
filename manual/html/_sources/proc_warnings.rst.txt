.. index:: coded warning; procedure, deprecation

Issue coded warnings
====================

.. rubric:: Purpose

To tell the user about a condition that does not stop the operation.

.. rubric:: Before you start

Select the correct tool. :numref:`tab-warning-choice` helps you.

.. list-table:: Selection of the tool for a warning
   :name: tab-warning-choice
   :widths: 55 45
   :header-rows: 1

   * - Condition
     - Tool
   * - The user of your function must be able to ignore the warning or to
       change it into an exception.
     - ``warn`` (this procedure)
   * - The condition is an event of the program, and filters are not
       necessary.
     - ``log.warning`` or ``log.event``. Refer to :doc:`proc_log`.

Issue a warning
---------------

.. rubric:: Procedure

1. Select a warning class: ``CodedWarning``, ``ConfigurationWarning``,
   ``DataQualityWarning`` or ``PerformanceWarning``.
2. Call the function ``warn`` with the code and the values for the
   replacement fields:

   .. code-block:: python
      :caption: A coded warning
      :name: ex-warn

      from annunciator import DataQualityWarning, warn

      def dead_time_correction(dead_time):
          if dead_time > 30:
              warn(code="APP-W-0002", category=DataQualityWarning,
                   stacklevel=2, dead_time=dead_time)
          return 1.0 / (1.0 - dead_time / 100.0)

3. Set ``stacklevel`` to 2. Then the warning identifies the line that
   called your function.
4. If the warning has no definition in a catalogue, give the message text
   as the first argument.

.. rubric:: Result

When the option ``capture_warnings`` is set, the log contains one
``WARNING`` event with the code. The logger name is ``py.warnings``. The
fields ``filename`` and ``lineno`` identify the line that called your
function.

.. note::

   Python shows the same warning from the same line only one time. This is
   the default behaviour of the standard ``warnings`` module.

Change a warning into an error in tests
---------------------------------------

.. rubric:: Procedure

1. Use the standard ``warnings`` module to set a filter:

   .. code-block:: python

      import warnings

      from annunciator import DataQualityWarning

      warnings.simplefilter("error", DataQualityWarning)

.. rubric:: Result

Each ``DataQualityWarning`` is now an exception. A test fails if the code
issues the warning.

Mark a function as deprecated
-----------------------------

.. rubric:: Procedure

1. Add the decorator ``deprecated`` to the old function. Give the version
   and the name of the replacement:

   .. code-block:: python

      from annunciator import deprecated

      @deprecated("2.0", alternative="load_spectrum", removal="3.0")
      def read_spectrum(path):
          return load_spectrum(path)

.. rubric:: Result

Each call of ``read_spectrum`` issues a ``DeprecatedFeatureWarning`` with
the code ``ANN-W-0309``. The warning identifies the line that called the
old function.
