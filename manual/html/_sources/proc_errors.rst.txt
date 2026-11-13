.. index:: coded error; procedure, exit status

Raise and catch coded errors
============================

.. rubric:: Purpose

To raise exceptions that have a message code, and to give the user the
cause and the remedy when the program catches them.

.. rubric:: Before you start

Define a message catalogue. Refer to :doc:`proc_catalogue`. The examples
use the catalogue of :numref:`ex-catalogue`.

Raise a coded error
-------------------

.. rubric:: Procedure

1. Select the class in :numref:`fig-hierarchy` that agrees with the
   condition. If no class agrees, use ``CodedError``.
2. Raise the class with the code and the values for the replacement
   fields:

   .. code-block:: python

      from annunciator import ResourceError

      raise ResourceError(code="APP-E-0001", name="HPGe-2")

3. If the error has no definition in a catalogue, give the message text.
   You can also give the cause and the remedy:

   .. code-block:: python

      from annunciator import ValidationError

      raise ValidationError(
          "The live time must be more than 0 s.",
          remedy="Set the live time to a positive value.",
          context={"live_time": live_time},
      )

.. rubric:: Result

The exception has the attributes ``code``, ``message``, ``severity``,
``cause``, ``remedy``, ``fields`` and ``context``. The text of the
exception starts with the code in square brackets.

Make your own error class
-------------------------

.. rubric:: Procedure

1. Make a subclass of ``CodedError`` or of one of its subclasses.
2. Set the class attribute ``default_code`` to the code of the usual
   message.
3. If the program is a command-line program, set ``exit_code``.

   .. code-block:: python
      :caption: An error class with a default code
      :name: ex-error-class

      from annunciator import ResourceError

      class DetectorError(ResourceError):
          """The detector does not operate."""

          default_code = "APP-E-0001"
          exit_code = 74

      raise DetectorError(name="HPGe-2")

.. rubric:: Result

The class makes the message text from the definition of ``APP-E-0001``.
You can catch the error as ``DetectorError``, ``ResourceError`` or
``CodedError``.

Catch a coded error
-------------------

.. rubric:: Procedure

1. Catch ``CodedError`` at the top level of the program.
2. Record the error with the method ``report``.
3. Show the result of the method ``describe`` to the user.
4. Stop the program with the attribute ``exit_code``.

   .. code-block:: python
      :caption: Top level of a command-line program
      :name: ex-main

      import sys

      from annunciator import CodedError, configure, get_logger

      def main() -> int:
          configure(level="INFO", file="logs/run.jsonl", file_format="json")
          log = get_logger("myapp")
          try:
              run_measurement()
          except CodedError as error:
              log.report(error)
              print(error.describe(), file=sys.stderr)
              return error.exit_code
          return 0

      if __name__ == "__main__":
          sys.exit(main())

.. rubric:: Result

When the program raises a coded error, the log contains one event with the
code and the traceback. The user sees the message, the cause and the
remedy:

.. code-block:: text

   [APP-E-0001] The detector 'HPGe-2' does not answer.
   Cause: The detector has no power or the cable is not connected.
   Remedy: Make sure that the detector has power. Examine the cable.

:numref:`tab-exit-codes` gives the exit status of each class.

Add context to an error that goes up
------------------------------------

.. rubric:: Procedure

1. Catch the error at the level that knows the context.
2. Call the method ``with_context``.
3. Raise the error again:

   .. code-block:: python

      try:
          analyse(sample)
      except CodedError as error:
          raise error.with_context(sample=sample.name)

.. rubric:: Result

The record of the error contains the field ``sample``.
