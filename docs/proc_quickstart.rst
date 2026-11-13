.. index:: quick start

Record your first events
========================

.. rubric:: Purpose

To write a small program that records information, a warning and an error.

.. rubric:: Before you start

Install the library. Refer to :doc:`installation`.

.. rubric:: Procedure

1. Make a file with the name ``first.py``.
2. Put this text in the file:

   .. code-block:: python
      :caption: A first program
      :name: ex-first

      from annunciator import configure, get_logger

      configure(level="INFO")
      log = get_logger("first")

      log.info("The measurement started.", sample="CeO2-04", live_time=600)
      log.warning("The dead time is high.", dead_time=0.31)
      try:
          value = 1 / 0
      except ZeroDivisionError as error:
          log.report(error, operation="ratio")

3. Run the program:

   .. code-block:: console

      python first.py

.. rubric:: Result

The terminal shows three events. The text is almost the same as this
example. The times and the paths are different.

.. code-block:: text

   2026-11-12T10:15:02.120Z INFO     first The measurement started. | sample=CeO2-04 live_time=600
   2026-11-12T10:15:02.121Z WARNING  first The dead time is high. | dead_time=0.31
   2026-11-12T10:15:02.121Z ERROR    first [ANN-E-0303] The operation 'ratio' failed: ZeroDivisionError: division by zero | operation=ratio exc_type=ZeroDivisionError
       Cause:  The operation raised an exception that does not have a message code.
       Remedy: Read the traceback in the log and correct the cause.
       Traceback (most recent call last):
         File "first.py", line 9, in <module>
           value = 1 / 0
       ZeroDivisionError: division by zero

Each line has the time, the severity, the logger name and the message. The
text after the vertical bar shows the structured fields.

.. rubric:: Subsequent steps

* To write the events to a file, do :doc:`proc_configure`.
* To give your own codes to messages, do :doc:`proc_catalogue`.
