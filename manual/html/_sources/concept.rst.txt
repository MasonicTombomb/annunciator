.. index:: concept of operations, data flow, severity, message code

Concept of operations
=====================

Function of the library
-----------------------

A program must tell its user what occurs. Some information is about normal progress.
Some information tells the user that a result is possibly incorrect. Some
information tells the user that an operation failed.

``annunciator`` gives one system for all this information. The system has
three primary functions:

Record
   The library records each event with a severity, a time, a text and
   structured data. It writes the events to the console, to a log file and
   to an event store in memory.

Explain
   Each message can have a message code. The code identifies a definition
   in a message catalogue. The definition gives the probable cause and the
   remedy. Thus the user knows what to do.

Handle
   The library gives tools that apply a standard policy to exceptions. The
   tools record an exception, change it into a different exception, try
   the operation again or collect it.

The library uses only the Python standard library. It operates together
with the standard ``logging`` module. Records from standard loggers go
through the same handlers.

Flow of data
------------

:numref:`fig-dataflow` shows how an event goes from your program to its
destinations.

.. figure:: figures/dataflow.*
   :name: fig-dataflow
   :width: 100%
   :alt: Flow of data from the program through the logger, the filters and
         the handlers to the console, the log file, the event store and the
         reports.

   Flow of data in the library

The flow has these stages:

1. Your program calls a method of a structured logger. A coded error, a
   coded warning or a hook can also start an event.
2. If the event has a message code, the logger gets the text, the cause
   and the remedy from the catalogue.
3. The logger adds the context data and makes a record.
4. The filters of each handler examine the record. A filter can accept,
   reject or change the record.
5. The formatter of each handler changes the record into text.
6. The handler writes the text to its destination.
7. The report functions and the command-line interface read the events.
   The source is the event store or a JSON Lines log file.

Parts of the library
--------------------

.. list-table:: Parts of the library
   :name: tab-parts
   :class: longtable
   :widths: 22 48 30
   :header-rows: 1

   * - Part
     - Function
     - Module
   * - Severity
     - Gives the importance of an event.
     - ``annunciator.levels``
   * - Structured logger
     - Records events with codes and fields.
     - ``annunciator.logger``
   * - Context
     - Adds the same data to all events of one operation.
     - ``annunciator.context``
   * - Message catalogue
     - Contains the definitions of the messages.
     - ``annunciator.catalogue``
   * - Coded error
     - An exception that has a code, a cause and a remedy.
     - ``annunciator.errors``
   * - Coded warning
     - A Python warning that has a code, a cause and a remedy.
     - ``annunciator.warns``
   * - Event
     - The structured form of one record.
     - ``annunciator.events``
   * - Handler
     - Sends records to a destination.
     - ``annunciator.handlers``
   * - Formatter
     - Changes a record into plain text, colour text or JSON.
     - ``annunciator.formatters``
   * - Filter
     - Accepts, rejects or changes records.
     - ``annunciator.filters``
   * - Configuration
     - Installs the handlers, the formatters, the filters and the hooks.
     - ``annunciator.config``
   * - Handling tools
     - Apply a policy to exceptions.
     - ``annunciator.handling``
   * - Hooks
     - Record exceptions that no code caught, and Python warnings.
     - ``annunciator.hooks``
   * - Reports
     - Read and select events, and make summaries.
     - ``annunciator.report``
   * - Flight recorder
     - Keeps detailed records and writes them when a failure occurs.
     - ``annunciator.recorder``
   * - Progress and watchdog
     - Record the progress of long operations and find stalls.
     - ``annunciator.watch``
   * - Runs
     - Record the manifest and the result of each run.
     - ``annunciator.provenance``
   * - Integrity
     - Makes and examines tamper-evident log files.
     - ``annunciator.integrity``
   * - Multiprocess tools
     - Send the records of many processes to one writer.
     - ``annunciator.multiprocess``
   * - Soft checks
     - Examine data and give coded messages.
     - ``annunciator.checks``
   * - Lint
     - Finds incorrect message codes in source code.
     - ``annunciator.lint``
   * - Test tools
     - Collect events in tests.
     - ``annunciator.testing``
   * - HTML report
     - Writes a report of a run for a browser.
     - ``annunciator.htmlreport``
   * - Command-line interface
     - Shows catalogues and examines log files.
     - ``annunciator.cli``
   * - Sphinx extension
     - Writes the message reference of your documentation.
     - ``annunciator.sphinxext``

Severity
--------

Each event has one of seven severities. :numref:`tab-severity-short` gives
the use of each severity. :doc:`ref_severity` gives the full data.

.. list-table:: Use of the severities
   :name: tab-severity-short
   :widths: 18 12 70
   :header-rows: 1

   * - Severity
     - Type
     - Use
   * - ``TRACE``, ``DEBUG``
     - Information
     - Data for a developer who looks for the cause of a fault.
   * - ``INFO``, ``NOTICE``
     - Information
     - Normal progress. ``NOTICE`` is for events that are important to the
       user.
   * - ``WARNING``
     - Warning
     - The program continues, but a result is possibly incorrect.
   * - ``ERROR``
     - Error
     - An operation did not complete. The program can continue with other
       operations.
   * - ``CRITICAL``
     - Error
     - The program cannot continue.

Message codes
-------------

A message code identifies one message definition. :numref:`fig-code` shows
the three parts of a code.

.. figure:: figures/code.*
   :name: fig-code
   :width: 70%
   :alt: The message code APP-E-0042 has the prefix APP, the severity
         letter E and the message number 0042.

   Structure of a message code

The prefix identifies the catalogue. Usually, one program or one package
has one catalogue. The severity letter is the first letter of the severity
name. The message number is unique in the catalogue.

A message definition contains four items:

* the code,
* the message text, with optional replacement fields such as ``{path}``,
* the probable cause,
* the remedy.

The same definition supplies the text of the log record, the text of the
exception and the text of the user documentation. Thus these three texts
always agree.

Coded errors and coded warnings
-------------------------------

A coded error is an exception with a message code. A coded warning is a
Python warning with a message code. :numref:`fig-hierarchy` shows the
classes that the library supplies. You can make your own subclasses.

.. figure:: figures/hierarchy.*
   :name: fig-hierarchy
   :width: 90%
   :alt: Class diagram. CodedError is a subclass of Exception. CodedWarning
         is a subclass of UserWarning. Each has subclasses for specific
         conditions.

   Classes of coded errors and coded warnings

Use an error when the operation cannot continue. Use a warning when the
operation continues but the user must know about a condition.

Error policy
------------

The handling tools apply the same policy to each exception.
:numref:`fig-policy` shows the policy of the ``handle_errors`` decorator
and the ``guard`` context manager.

.. figure:: figures/policy.*
   :name: fig-policy
   :width: 75%
   :alt: Decision diagram. A handled exception is recorded, then on_error
         is called. If wrap is given, a new exception is raised. If reraise
         is True, the initial exception is raised again. If not, the
         default value is returned.

   Policy of ``handle_errors`` and ``guard``

The library records each exception object only one time. If an exception
goes through two handling tools, the log contains one record.

Functions for long runs and for evidence
----------------------------------------

Version 1.1.0 added functions that standard log tools do not usually
have. They answer four questions.

What occurred before the failure?
   The flight recorder keeps the last detailed records in memory. It
   writes them only when a failure occurs. Refer to :numref:`fig-recorder`.

Does the run continue?
   Progress records show the rate and the remaining time. A watchdog
   records a warning when an operation makes no progress.

Can a different person do the same run again?
   A run manifest records the software versions, the source revision, the
   configuration and the seed.

Is the log file the same as when the program wrote it?
   A chain of hashes connects the records. A change, a removal or an
   addition breaks the chain.

:doc:`proc_longrun` and :doc:`proc_runs` give the procedures.

Relation to the standard ``logging`` module
-------------------------------------------

A structured logger is a thin layer on a standard logger with the same
name. Thus these conditions apply:

* Modules that use ``logging.getLogger`` send their records through the
  handlers of the library.
* Handlers from other packages receive the records of structured loggers.
* The severities have the same numeric values as the standard levels.

The library does not change the root logger before you call
``configure``.
