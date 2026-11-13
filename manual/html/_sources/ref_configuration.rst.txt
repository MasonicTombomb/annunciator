.. index:: configuration; reference, options, environment variable; reference

Configuration options
=====================

This section gives all options of the class ``LogConfig``. You can give
each option in three ways:

* as a keyword argument of ``configure`` or ``LogConfig``,
* as a key in a TOML file or a JSON file,
* as an environment variable with the name ``ANNUNCIATOR_`` and the option
  name in capital letters.

If an option name is not known, the library raises :msg:`ANN-E-0001`. If a
value is not permitted, the library raises :msg:`ANN-E-0002`.

General options
---------------

.. list-table:: General options
   :name: tab-options-general
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``level``
     - severity
     - ``"INFO"``
     - The minimum severity that the library records.
   * - ``logger_name``
     - text
     - ``""``
     - The logger that gets the handlers. The empty text selects the root
       logger.
   * - ``logger_levels``
     - table
     - empty
     - The minimum severity for named loggers. The keys are logger names.
   * - ``utc``
     - boolean
     - ``true``
     - If true, the time is in UTC. If false, the time is the local time
       with its UTC offset.
   * - ``asynchronous``
     - boolean
     - ``false``
     - If true, a different thread writes the events. Use this option when
       a slow destination must not delay the program.
   * - ``store_capacity``
     - integer
     - ``1000``
     - The number of events in the event store. The value 0 selects no
       event store.
   * - ``install_hooks``
     - boolean
     - ``true``
     - If true, the library records exceptions that no code caught.
   * - ``capture_warnings``
     - boolean
     - ``true``
     - If true, the library records Python warnings.

Console options
---------------

.. list-table:: Console options
   :name: tab-options-console
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``console``
     - boolean
     - ``true``
     - If true, the library writes events to the console.
   * - ``console_level``
     - severity
     - none
     - The minimum severity for the console. Without a value, the library
       uses ``level``.
   * - ``console_format``
     - text
     - ``"auto"``
     - ``"auto"``, ``"plain"``, ``"colour"`` or ``"json"``. ``"auto"``
       selects ``"colour"`` on a terminal and ``"plain"`` in all other
       conditions.
   * - ``split_streams``
     - boolean
     - ``true``
     - If true, ``WARNING`` and higher go to ``stderr`` and all lower
       severities go to ``stdout``. If false, all events go to ``stderr``.

.. note::

   The environment variable ``NO_COLOR`` stops the colour in the mode
   ``"auto"``. The environment variable ``FORCE_COLOR`` selects the
   colour in the mode ``"auto"``.

File options
------------

.. list-table:: File options
   :name: tab-options-file
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``file``
     - path
     - none
     - The path of the log file. Without a value, the library writes no
       log file.
   * - ``file_level``
     - severity
     - none
     - The minimum severity for the log file. Without a value, the library
       uses ``level``.
   * - ``file_format``
     - text
     - ``"plain"``
     - ``"plain"`` or ``"json"``. Use ``"json"`` for a file that the
       report functions must read.
   * - ``rotate``
     - text
     - ``"size"``
     - ``"none"``, ``"size"`` or ``"time"``.
   * - ``max_bytes``
     - integer
     - ``10000000``
     - For the rotation by size: the maximum size of the file in bytes.
   * - ``when``
     - text
     - ``"midnight"``
     - For the rotation by time: the interval. The permitted values are
       those of the standard class ``TimedRotatingFileHandler``.
   * - ``backup_count``
     - integer
     - ``5``
     - The number of old log files that the library keeps.
   * - ``encoding``
     - text
     - ``"utf-8"``
     - The text encoding of the log file.

.. caution::

   When the rotation removes an old log file, the events in that file are
   lost. Set ``backup_count`` to a value that keeps the files for the
   necessary time.

Text options
------------

These options apply to the formats ``"plain"`` and ``"colour"``.

.. list-table:: Text options
   :name: tab-options-text
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``show_fields``
     - boolean
     - ``true``
     - If true, the text shows the structured fields after a vertical bar.
   * - ``show_help``
     - boolean
     - ``true``
     - If true, the text shows the cause and the remedy for ``WARNING``
       and higher.
   * - ``show_source``
     - boolean
     - ``false``
     - If true, the text shows the source file and the line number.

Filter options
--------------

The text about the default value of ``redact_keys`` is after
:numref:`tab-options-diagnostic`.

.. list-table:: Filter options
   :name: tab-options-filters
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``redact_keys``
     - list of text
     - See below
     - Parts of field names that identify secret data. Letter case is not
       important.
   * - ``redact_patterns``
     - list of text
     - empty
     - Regular expressions for secret text in messages and in text values.
   * - ``duplicate_window``
     - number
     - ``0``
     - The time window in seconds. In this window, the library rejects
       equal records. The value 0 selects no duplicate filter.
   * - ``rate_limit``
     - number
     - ``0``
     - The maximum mean number of records each second. The value 0 selects
       no limit. The limit does not apply to ``ERROR`` and higher.
   * - ``rate_burst``
     - integer
     - ``100``
     - The maximum number of records at one time for the rate limit.

Diagnostic options
------------------

.. list-table:: Diagnostic options
   :name: tab-options-diagnostic
   :widths: 22 14 14 50
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Function
   * - ``flight_recorder``
     - integer
     - ``0``
     - The number of detailed records that the flight recorder keeps in
       memory. The value 0 selects no flight recorder.
   * - ``flight_level``
     - severity
     - ``"DEBUG"``
     - The minimum severity of the records that the flight recorder
       keeps.
   * - ``flight_trigger``
     - severity
     - ``"ERROR"``
     - The severity that causes the flight recorder to write the kept
       records.
   * - ``file_chain``
     - boolean
     - ``false``
     - If true, each record of the log file contains integrity data. The
       option ``file_format`` must be ``"json"``.
   * - ``capture_locals``
     - boolean
     - ``false``
     - If true, each event with a traceback contains the local variables
       of the last two functions.

The flight recorder is on the log file. If the configuration has no log
file, the flight recorder is on the console.

The environment variable ``ANNUNCIATOR_CHAIN_KEY`` supplies the key for the
integrity data. It is not an option of ``LogConfig``. Thus a configuration
file does not contain the key.

The default value of ``redact_keys`` is: ``password``, ``passwd``,
``secret``, ``token``, ``api_key``, ``apikey``, ``authorization``,
``credential``, ``private_key``.

Format of environment variables
-------------------------------

.. list-table:: Values of environment variables
   :name: tab-env
   :widths: 16 32 52
   :header-rows: 1

   * - Option type
     - Permitted text
     - Example
   * - boolean
     - ``1``, ``true``, ``yes``, ``on``, ``0``, ``false``, ``no``, ``off``
     - ``ANNUNCIATOR_CONSOLE=off``
   * - integer, number
     - Digits
     - ``ANNUNCIATOR_BACKUP_COUNT=14``
   * - list of text
     - Items with commas between them
     - ``ANNUNCIATOR_REDACT_KEYS=password,pin``
   * - table
     - ``name=LEVEL`` items with commas between them
     - ``ANNUNCIATOR_LOGGER_LEVELS=numba=WARNING``
