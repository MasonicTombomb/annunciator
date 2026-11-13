.. index:: plain text format, JSON Lines; format, catalogue file, CSV; format

Record formats and file formats
===============================

Plain text format
-----------------

The formats ``"plain"`` and ``"colour"`` write one primary line for each
event:

.. code-block:: text

   TIME SEVERITY LOGGER [CODE] MESSAGE | KEY=VALUE ... (FILE:LINE)

.. list-table:: Parts of the primary line
   :name: tab-plain
   :widths: 22 78
   :header-rows: 1

   * - Part
     - Contents
   * - ``TIME``
     - The time in the ISO 8601 format with milliseconds. The suffix ``Z``
       shows that the time is in UTC.
   * - ``SEVERITY``
     - The severity name in a column of eight characters.
   * - ``LOGGER``
     - The name of the logger.
   * - ``[CODE]``
     - The message code. This part is absent for an event without a code.
   * - ``MESSAGE``
     - The message text.
   * - ``KEY=VALUE``
     - The structured fields. The option ``show_fields`` controls this
       part.
   * - ``(FILE:LINE)``
     - The source position. The option ``show_source`` controls this
       part.

Indented lines can follow the primary line, in this sequence:

1. ``Cause:`` and the probable cause.
2. ``Remedy:`` and the corrective action.
3. The traceback of a related exception.

The lines ``Cause:`` and ``Remedy:`` occur only for the severity
``WARNING`` and higher.

JSON Lines format
-----------------

The format ``"json"`` writes one JSON object on each line.
:numref:`tab-json` gives the keys of the object. The object does not
contain keys that have no value.

.. list-table:: Keys of an event object
   :name: tab-json
   :class: longtable
   :widths: 18 14 68
   :header-rows: 1

   * - Key
     - Type
     - Contents
   * - ``timestamp``
     - text
     - The time in UTC, in the ISO 8601 format with the suffix ``Z``.
   * - ``severity``
     - text
     - The severity name.
   * - ``level``
     - number
     - The numeric value of the severity.
   * - ``code``
     - text
     - The message code.
   * - ``logger``
     - text
     - The name of the logger.
   * - ``message``
     - text
     - The message text.
   * - ``fields``
     - object
     - The structured fields and the context data.
   * - ``cause``
     - text
     - The probable cause.
   * - ``remedy``
     - text
     - The corrective action.
   * - ``exception``
     - object
     - Data about a related exception. Refer to :numref:`tab-json-exception`.
   * - ``source``
     - object
     - The keys ``file``, ``line``, ``function`` and ``module``.
   * - ``process``
     - number
     - The identifier of the process.
   * - ``thread``
     - text
     - The name of the thread.
   * - ``event_id``
     - text
     - A unique identifier of the event.
   * - ``chain``
     - object
     - The integrity data. Refer to :numref:`tab-json-chain`. The option
       ``file_chain`` controls this key.

.. list-table:: Keys of the object ``exception``
   :name: tab-json-exception
   :widths: 18 14 68
   :header-rows: 1

   * - Key
     - Type
     - Contents
   * - ``type``
     - text
     - The name of the exception class.
   * - ``message``
     - text
     - The text of the exception.
   * - ``fingerprint``
     - text
     - Twelve hexadecimal characters that identify the type of failure.
   * - ``traceback``
     - text
     - The traceback.
   * - ``locals``
     - object
     - The local variables. Each key identifies a function, a file and a
       line. The option ``capture_locals`` controls this key.

.. list-table:: Keys of the object ``chain``
   :name: tab-json-chain
   :widths: 18 14 68
   :header-rows: 1

   * - Key
     - Type
     - Contents
   * - ``seq``
     - number
     - The sequence number of the record. The first record has the
       number 1.
   * - ``prev``
     - text
     - The hash of the record before this record. For the first record,
       the value is 64 zeros.
   * - ``hash``
     - text
     - The hash of ``prev``, ``seq`` and the other keys of the record.

The hash function is SHA-256. With a key, the function is HMAC-SHA-256. The
library calculates the hash from the JSON text of the record with sorted
keys and without spaces.

.. code-block:: json
   :caption: One event in the JSON Lines format (shown on many lines)
   :name: ex-json

   {
     "timestamp": "2026-11-12T10:15:02.454Z",
     "severity": "WARNING",
     "level": 30,
     "code": "APP-W-0002",
     "logger": "myapp.daq",
     "message": "The dead time is 31 %.",
     "fields": {"run": "R-17", "dead_time": 31},
     "cause": "The count rate is too high for the detector.",
     "remedy": "Increase the distance between the source and the detector.",
     "source": {"file": "daq.py", "line": 88, "function": "acquire", "module": "daq"},
     "process": 4112,
     "thread": "MainThread",
     "event_id": "bd4649eafecf4ec1"
   }

If a field value has a type that JSON cannot contain, the library converts
the value to text.

Catalogue file format
---------------------

A catalogue file is a JSON file or a TOML file. The method
``MessageCatalogue.save`` writes the JSON form. The method
``MessageCatalogue.load`` reads the two forms.

.. list-table:: Keys of a catalogue file
   :name: tab-catalogue-file
   :widths: 22 14 64
   :header-rows: 1

   * - Key
     - Necessary
     - Contents
   * - ``prefix``
     - Yes
     - The catalogue prefix.
   * - ``title``
     - No
     - A short title for the documentation.
   * - ``messages``
     - No
     - A list of message objects.
   * - ``messages.code``
     - Yes
     - The message code.
   * - ``messages.text``
     - Yes
     - The message text, with optional replacement fields.
   * - ``messages.cause``
     - No
     - The probable cause.
   * - ``messages.remedy``
     - No
     - The corrective action.
   * - ``messages.category``
     - No
     - A group name.
   * - ``messages.since``
     - No
     - The version of your software that added the message.

.. code-block:: json
   :caption: A catalogue file in the JSON form
   :name: ex-catalogue-file

   {
     "prefix": "APP",
     "title": "Messages of the spectrum tools",
     "messages": [
       {
         "code": "APP-E-0001",
         "text": "The detector '{name}' does not answer.",
         "cause": "The detector has no power or the cable is not connected.",
         "remedy": "Make sure that the detector has power. Examine the cable."
       }
     ]
   }

CSV format
----------

The function ``export_csv`` and the command ``view --csv`` write a CSV file
with one row for each event. The columns are, in this sequence:
``timestamp``, ``severity``, ``code``, ``logger``, ``message``, ``cause``,
``remedy``, ``exception_type``, ``exception_message``, ``fields``. The
column ``fields`` contains the structured fields as JSON text.

Run manifest
------------

The function ``start_run`` records the manifest in the field ``manifest``
of the event ``ANN-N-0401``. The method ``Run.save_manifest`` writes the
same data to a JSON file, with the result of the run.

.. list-table:: Keys of a run manifest
   :name: tab-manifest
   :class: longtable
   :widths: 22 78
   :header-rows: 1

   * - Key
     - Contents
   * - ``annunciator``
     - The version of this library.
   * - ``python``, ``implementation``
     - The version and the type of the Python interpreter.
   * - ``platform``, ``host``
     - The operating system and the name of the computer.
   * - ``executable``, ``argv``, ``cwd``
     - The Python program file, the command line and the current
       directory.
   * - ``pid``
     - The identifier of the process.
   * - ``started``
     - The start time in UTC.
   * - ``packages``
     - The versions of the packages that you named.
   * - ``seed``
     - The seed that you gave.
   * - ``git``
     - The keys ``commit`` and ``dirty``. ``dirty`` is true if the source
       directory has changes that are not committed.
   * - ``config_hash``
     - A short hash of the configuration in use.
   * - ``extra``
     - The other keyword arguments of ``start_run``.
   * - ``user``
     - The login name. Only with ``include_user``.

The file of ``save_manifest`` also contains the keys ``run``, ``run_id``,
``status``, ``elapsed``, ``errors`` and ``warnings``.

HTML report
-----------

The function ``write_html_report`` and the command ``report --html`` write
one HTML file. The file contains the page, its style and the events. It
does not load data from a network. The file contains a maximum of 20000
events by default. The counts at the top of the page include all events.
