.. index:: audience, conventions, Simplified Technical English

Information for use of this manual
==================================

Purpose of the manual
---------------------

This manual gives the instructions and the reference data for the
``annunciator`` library. It tells you how to do these tasks:

* install the library,
* record information, warnings and errors,
* define messages that have a code, a cause and a remedy,
* handle exceptions with a standard policy,
* examine log files,
* monitor long runs and compare runs,
* show that a log file did not change,
* find the cause of a message and correct the problem.

Audience
--------

The manual is for two groups of users.

Developers
   Persons who write Python programs that use the library. You must know
   how to write Python functions and classes. You must know how to use
   exceptions. Knowledge of the standard ``logging`` module helps, but it is
   not necessary.

Operators
   Persons who run a program that uses the library and who read its
   messages and its log files. You must know how to use a terminal.
   Knowledge of Python is not necessary. Read :doc:`messages` and
   :doc:`ref_cli`.

Scope
-----

The manual includes the full function of version |release| of the library.
It does not give instructions for Python, for the standard ``logging``
module or for Sphinx. :doc:`related` tells you where to find those
instructions.

How to use the manual
---------------------

.. list-table:: Where to find information
   :name: tab-where
   :widths: 45 55
   :header-rows: 1

   * - If you must
     - Read
   * - Know what the library does and how its parts operate together
     - :doc:`concept`
   * - Install, upgrade or remove the library
     - :doc:`installation`
   * - Do a task for the first time
     - :doc:`procedures`
   * - Find the permitted values of an option, a command or a parameter
     - :doc:`reference`
   * - Know the meaning of a message code and the corrective action
     - :doc:`messages`
   * - Know the meaning of a term
     - :doc:`glossary`

Each procedure has the same structure:

Purpose
   The result that the procedure gives.

Before you start
   The conditions that are necessary before the first step.

Procedure
   The steps, in a numbered list. Do the steps in the given sequence.

Result
   The condition that shows that the procedure was successful.

Conventions
-----------

.. list-table:: Typographic conventions
   :name: tab-conventions
   :widths: 30 70
   :header-rows: 1

   * - Convention
     - Meaning
   * - ``monospace text``
     - Text that you type, text that the computer shows, and names in the
       program code.
   * - ``UPPER_CASE`` in a command
     - A value that you must replace, for example ``FILE``.
   * - ``[text]`` in a command
     - An optional part of a command.
   * - ``>>>``
     - The prompt of the interactive Python interpreter. Do not type it.
   * - ``$`` or a line without prompt in a ``console`` block
     - A command for the terminal.

Critical information
--------------------

The manual uses two types of critical information. The use of this software
cannot cause injury to persons. Thus the manual contains no warnings.

.. caution::

   A caution tells you that data loss, disclosure of secret data or an
   incorrect result is possible. Obey the instruction in the caution.

.. note::

   A note gives you information that helps you to do a task.

A caution or a note that applies to a step comes immediately before that
step.

Language
--------

The text of this manual obeys the writing rules of ASD-STE100 Simplified
Technical English, Issue 9. The spelling is British English.

The names in :numref:`tab-technical-names` are technical names in this
manual. The verbs in :numref:`tab-technical-verbs` are technical verbs.
:doc:`glossary` gives the definitions of the technical names.

.. list-table:: Technical names
   :name: tab-technical-names
   :widths: 30 70
   :header-rows: 1

   * - Category
     - Technical names
   * - Parts of the library
     - catalogue, coded error, coded warning, context, event, event store,
       field, filter, formatter, handler, hook, logger, message code, record,
       report, severity
   * - Functions for runs
     - chain, fingerprint, flight recorder, manifest, run, soft check,
       stall, watchdog
   * - Python terms
     - argument, attribute, class, context manager, coroutine, decorator,
       exception, fixture, function, local variable, method, module,
       package, parameter, process, queue, subclass, thread, traceback,
       warning
   * - Computer terms
     - browser, command, console, directory, environment variable, file,
       hash, HTML, JSON, JSON Lines, key, log, option, path, prefix, seed,
       terminal, TOML

.. list-table:: Technical verbs
   :name: tab-technical-verbs
   :widths: 30 70
   :header-rows: 1

   * - Verb
     - Meaning in this manual
   * - call
     - To start a function or a method.
   * - catch
     - To stop an exception in an ``except`` block.
   * - configure
     - To set the options of the library.
   * - format
     - To change a record into text.
   * - import
     - To load a Python module.
   * - raise
     - To start an exception.
   * - return
     - To give a value to the code that called a function.
   * - run
     - To start a program or a command.
   * - type
     - To enter text with the keyboard.

Comments on the manual
----------------------

If you find an error in this manual, send a report to the issuer. Include
the document number, the issue and the section number.
