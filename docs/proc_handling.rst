.. index:: error policy; procedure, retry, error collector, guard, timed

Apply an error policy
=====================

.. rubric:: Purpose

To handle exceptions in the same way in all parts of a program.

.. rubric:: Before you start

Read :ref:`the description of the error policy <fig-policy>` in
:doc:`concept`. Then select the tool in :numref:`tab-handling-choice`.

.. list-table:: Selection of the handling tool
   :name: tab-handling-choice
   :widths: 55 45
   :header-rows: 1

   * - Task
     - Tool
   * - Record all exceptions of a function
     - ``handle_errors``
   * - Record all exceptions of a block of code
     - ``guard``
   * - Do an operation again when it fails
     - ``retry``
   * - Continue after an error and show all errors at the end
     - ``ErrorCollector``
   * - Record the duration of a block of code
     - ``timed``
   * - Record each call of a function
     - ``log_calls``

Record the exceptions of a function
-----------------------------------

.. rubric:: Procedure

1. Add the decorator ``handle_errors`` to the function.
2. Give the exception classes that the decorator must handle.
3. Select the policy with the parameters ``reraise``, ``default`` and
   ``wrap``. :numref:`tab-policy-params` gives the effect.

   .. code-block:: python
      :caption: Three policies for ``handle_errors``
      :name: ex-handle

      from annunciator import DataError, handle_errors

      # Record the exception, then raise it again (default).
      @handle_errors(OSError)
      def load(path):
          return open(path, "rb").read()

      # Record the exception, then return a default value.
      @handle_errors(ZeroDivisionError, reraise=False, default=float("nan"))
      def ratio(a, b):
          return a / b

      # Record the exception, then raise a coded error from it.
      @handle_errors(KeyError, IndexError, wrap=DataError)
      def channel(spectrum, index):
          return spectrum[index]

.. list-table:: Policy parameters
   :name: tab-policy-params
   :widths: 30 70
   :header-rows: 1

   * - Parameters
     - Effect after the record
   * - No parameter
     - The decorator raises the initial exception again.
   * - ``wrap=CLASS``
     - The decorator raises ``CLASS`` from the initial exception.
   * - ``reraise=False``
     - The decorator returns ``default``. The exception stops.

.. rubric:: Result

Each handled exception makes one event with the traceback. A coded error
keeps its code. All other exceptions get the code ``ANN-E-0303``.

.. caution::

   Use ``reraise=False`` only when the default value is a correct result
   for the code that called the function. If not, the program continues
   with incorrect data.

Record the exceptions of a block
--------------------------------

.. rubric:: Procedure

1. Put the block in a ``with guard(...)`` statement. Give a name for the
   operation:

   .. code-block:: python

      from annunciator import guard

      with guard(OSError, operation="write summary", reraise=False) as result:
          write_summary(path)
      if result.failed:
          print("The summary is not available.")

.. rubric:: Result

If the block raises an ``OSError``, the log contains one event. The
attribute ``failed`` is ``True`` and the program continues after the
block.

Do an operation again
---------------------

.. rubric:: Procedure

1. Add the decorator ``retry`` to the function.
2. Give only the exception classes of temporary conditions.
3. Set the number of attempts and the delay:

   .. code-block:: python
      :caption: Retry with an increasing delay
      :name: ex-retry

      from annunciator import retry

      @retry(ConnectionError, TimeoutError, attempts=4, delay=0.5, backoff=2.0)
      def read_register(address):
          return instrument.query(address)

.. rubric:: Result

The delays before attempts 2, 3 and 4 are 0.5 s, 1 s and 2 s. Each failed
attempt makes one ``WARNING`` event with the code ``ANN-W-0301``. If
attempt 4 fails, the decorator records ``ANN-E-0302``. Then it raises
``RetryExhaustedError`` from the last exception.

.. caution::

   Do not use ``retry`` for an operation that is not safe to do two
   times. An example is an operation that moves a motor by a relative
   distance.

Collect many errors
-------------------

.. rubric:: Procedure

1. Make an ``ErrorCollector`` with the name of the operation.
2. Put each item of work in a ``with collector.catch(...)`` block.
3. After the loop, call ``raise_if_errors``:

   .. code-block:: python
      :caption: Collection of errors
      :name: ex-collector

      from annunciator import ErrorCollector

      collector = ErrorCollector("import spectra")
      for path in paths:
          with collector.catch(OSError, ValueError, path=str(path)):
              spectra.append(load(path))
      print(collector.summary())
      collector.raise_if_errors()

.. rubric:: Result

The loop examines all paths. Each error makes one event. If one or more
errors occurred, ``raise_if_errors`` raises ``AggregateError`` with the
code ``ANN-E-0304``. The attribute ``errors`` contains the exceptions.

Record durations and calls
--------------------------

.. rubric:: Procedure

1. To record the duration of a block, use ``timed``. Set ``warn_after``
   to get a warning for a slow block:

   .. code-block:: python

      from annunciator import timed

      with timed("peak fit", warn_after=5.0, peaks=12):
          fit_peaks(spectrum)

2. To record each call of a function, add the decorator ``log_calls``:

   .. code-block:: python

      from annunciator import log_calls

      @log_calls(arguments=True)
      def calibrate(energy, channel):
          ...

.. caution::

   The option ``arguments`` records all arguments of the function. Do not
   use this option for a function that gets secret data.

.. rubric:: Result

Step 1 records ``ANN-I-0308`` with the duration. If the duration is more
than 5 s, it records ``ANN-W-0305``. Step 2 records ``ANN-D-0306`` and
``ANN-D-0307`` with the severity ``DEBUG``.
