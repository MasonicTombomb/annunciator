Glossary
========

.. glossary::
   :sorted:

   catalogue
   message catalogue
      A set of message definitions that have the same prefix.

   cause
      The text that gives the probable reason for an event. It is a part of
      a message definition.

   chain
      The sequence of hashes that connects the records of a log file. Each
      record contains the hash of the record before it.

   coded error
      An exception that has a message code, a cause and a remedy. All coded
      errors are subclasses of ``CodedError``.

   coded warning
      A Python warning that has a message code, a cause and a remedy. All
      coded warnings are subclasses of ``CodedWarning``.

   context
      Key and value pairs that the library adds to all events of one
      thread or one task.

   correlation identifier
      A unique text in the context. It lets you find all events of one
      operation.

   error policy
      The rule that tells a handling tool what to do with an exception
      after the record. The tool can raise it again, change it or stop it.

   event
      One occurrence that the library recorded. An event has a time, a
      severity, a message and optional structured data.

   event store
      A handler that keeps the last events in memory.

   field
   structured field
      A key and value pair that is a part of an event.

   fingerprint
      A short identifier of a type of failure. Exceptions with the same
      class and the same sequence of functions have the same fingerprint.

   flight recorder
      A handler that keeps the last detailed records in memory and writes
      them when a failure occurs.

   filter
      An object that accepts, rejects or changes a record before a handler
      writes it.

   formatter
      An object that changes a record into text.

   handler
      An object that sends records to a destination, for example the
      console or a file.

   hook
      A function that Python calls when an exception has no handler or
      when a module issues a warning.

   JSON Lines
      A text file format. Each line of the file is one JSON object.

   logger
   structured logger
      An object with methods that record events. Each logger has a name.

   manifest
   run manifest
      The data that identify the environment of a run: the software
      versions, the source revision, the configuration and the seed.

   message code
      The unique identifier of a message definition, for example
      ``APP-E-0042``.

   message definition
      The code, the text, the cause and the remedy of one message.

   prefix
      The first part of a message code. It identifies the catalogue.

   record
      The object that the standard ``logging`` module makes for one log
      call. The library changes a record into an event.

   redaction
      The replacement of secret data in a record with the text
      ``[REDACTED]``.

   remedy
      The text that gives the corrective action for an event. It is a part
      of a message definition.

   replacement field
      A name in braces in a message text, for example ``{path}``. The
      library puts a value in its position.

   rotation
      The procedure that closes a full log file, gives it a new name and
      starts a new file.

   run
      One complete operation of a program, for example one measurement or
      one simulation.

   soft check
      A function that examines a condition on data. It raises an error or
      records a warning when the condition is not true.

   stall
      The condition of an operation that makes no progress but does not
      raise an exception.

   watchdog
      An object that records a warning when an operation makes no progress
      in a permitted time.

   severity
      The importance of an event. The library has seven severities, from
      ``TRACE`` to ``CRITICAL``.

   traceback
      The list of function calls that were active when an exception
      occurred.

Abbreviations
-------------

.. list-table:: Abbreviations
   :name: tab-abbreviations
   :widths: 20 80
   :header-rows: 1

   * - Abbreviation
     - Meaning
   * - ANSI
     - American National Standards Institute
   * - API
     - Application programming interface
   * - ASD
     - AeroSpace, Security and Defence Industries Association of Europe
   * - CSV
     - Comma-separated values
   * - HMAC
     - Hash-based message authentication code
   * - HTML
     - HyperText Markup Language
   * - JSON
     - JavaScript Object Notation
   * - PDF
     - Portable Document Format
   * - SHA
     - Secure Hash Algorithm
   * - STE
     - Simplified Technical English
   * - TOML
     - Tom's Obvious, Minimal Language
   * - UTC
     - Coordinated Universal Time
