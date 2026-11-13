.. index:: report; procedure, event store; procedure, CSV

Examine and summarise a log
===========================

.. rubric:: Purpose

To find events in a log and to make a summary of a run.

.. rubric:: Before you start

For the procedures that use a log file, configure a file with the option
``file_format`` set to ``"json"``. Refer to :doc:`proc_configure`.

Make a summary at the end of a program
--------------------------------------

.. rubric:: Procedure

1. Call ``summarise`` without arguments before the program stops.
2. Show the text of the report.
3. Use the method ``exit_code`` for the exit status of the program:

   .. code-block:: python
      :caption: Summary at the end of a program
      :name: ex-summary

      import sys

      from annunciator import summarise

      report = summarise()
      print(report.to_text())
      sys.exit(report.exit_code())

.. rubric:: Result

The terminal shows the number of events for each severity and for each
message code:

.. code-block:: text

   Events: 14
   Worst severity: ERROR
   First event: 2026-11-12T13:45:26+00:00
   Last event:  2026-11-12T13:45:26+00:00
   By severity:
     ERROR    6
     WARNING  5
     INFO     1
     DEBUG    2
   By message code:
     ANN-E-0303       3
     APP-E-0001       2

.. note::

   The summary uses the event store. The store keeps the last 1000 events
   by default. To keep more events, increase the option
   ``store_capacity``.

Examine a log file in the terminal
----------------------------------

.. rubric:: Procedure

1. Show a summary of the file:

   .. code-block:: console

      annunciator report logs/run.jsonl

2. Show only the events of the severity ``WARNING`` and higher:

   .. code-block:: console

      annunciator view logs/run.jsonl --min-severity WARNING

3. Show only the events of your catalogue that are errors:

   .. code-block:: console

      annunciator view logs/run.jsonl --code "APP-E-*"

4. Write the selected events to a CSV file for a spreadsheet:

   .. code-block:: console

      annunciator view logs/run.jsonl --min-severity WARNING --csv problems.csv

.. rubric:: Result

Steps 2 and 3 show the events in the plain text format. The exit status of
step 1 is 0, 1 or 2. :doc:`ref_cli` gives the meaning.

Examine events in a program
---------------------------

.. rubric:: Procedure

1. Read the events with ``read_events``, or get them from the event
   store.
2. Select the events with ``select_events``:

   .. code-block:: python

      from annunciator import get_store, read_events, select_events

      # From a log file.
      slow = select_events(read_events("logs/run.jsonl"), code="ANN-W-0305")
      for event in slow:
          print(event.timestamp, event.fields["operation"], event.fields["elapsed"])

      # From the event store of the program.
      problems = get_store().select(minimum="WARNING")

.. rubric:: Result

``select_events`` gives the events one at a time. ``select`` returns a
list. Each item is an ``Event`` object. :doc:`ref_formats` gives its
attributes.

Send events to a different system
---------------------------------

.. rubric:: Procedure

1. Write a function that accepts one ``Event``.
2. Add a ``CallbackHandler`` with that function to the root logger:

   .. code-block:: python

      import logging

      from annunciator import Severity
      from annunciator.handlers import CallbackHandler

      def show_in_status_bar(event):
          status_bar.set_text(f"{event.severity.name}: {event.message}")

      logging.getLogger().addHandler(
          CallbackHandler(show_in_status_bar, level=Severity.WARNING)
      )

.. rubric:: Result

The library calls the function for each event of the severity ``WARNING``
and higher.
