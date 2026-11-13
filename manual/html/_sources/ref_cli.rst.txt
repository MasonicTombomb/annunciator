.. index:: command-line interface, commands, exit status; commands

Command-line interface
======================

Syntax
------

.. code-block:: text

   annunciator [--version] [-i MODULE] [-c FILE] COMMAND [ARGUMENTS]

If the terminal cannot find the command ``annunciator``, use
``python -m annunciator`` with the same arguments.

General options
---------------

Put the general options before the command.

.. list-table:: General options of the command-line interface
   :name: tab-cli-options
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--version``
     - Shows the version of the library.
   * - ``-h``, ``--help``
     - Shows the help text. You can also put this option after a command.
   * - ``-i MODULE``, ``--import MODULE``
     - Imports a module that defines message catalogues. You can give this
       option more than one time.
   * - ``-c FILE``, ``--catalogue-file FILE``
     - Reads a message catalogue from a JSON file or a TOML file. You can
       give this option more than one time.

Commands
--------

``catalogue``
~~~~~~~~~~~~~

Shows the messages of the registered catalogues.

.. code-block:: text

   annunciator catalogue [--prefix PREFIX] [--min-severity SEVERITY]
                         [--search TEXT] [--format {text,json,rst}]

.. list-table:: Options of the command ``catalogue``
   :name: tab-cli-catalogue
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--prefix PREFIX``
     - Shows only the catalogue that has this prefix.
   * - ``--min-severity SEVERITY``
     - Shows only the messages of this severity or higher.
   * - ``--search TEXT``
     - Shows only the messages that contain this text.
   * - ``--format FORMAT``
     - ``text`` (default), ``json`` or ``rst``.

``explain``
~~~~~~~~~~~

Shows the full definition of one message.

.. code-block:: text

   annunciator explain CODE

``report``
~~~~~~~~~~

Shows a summary of a JSON Lines log file.

.. code-block:: text

   annunciator report PATH [--json] [--html FILE] [--title TEXT] [SELECTION]

.. list-table:: Options of the command ``report``
   :name: tab-cli-report
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--json``
     - Writes the summary as a JSON object.
   * - ``--html FILE``
     - Also writes an HTML report of the selected events to the file.
   * - ``--title TEXT``
     - The title of the HTML report.

``view``
~~~~~~~~

Shows the events of a JSON Lines log file in the plain text format.

.. code-block:: text

   annunciator view PATH [--no-help] [--csv FILE] [SELECTION]

.. list-table:: Options of the command ``view``
   :name: tab-cli-view
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--no-help``
     - Does not show the cause and the remedy.
   * - ``--csv FILE``
     - Writes the selected events to a CSV file and shows no events.

``check-config``
~~~~~~~~~~~~~~~~

Examines a configuration file and shows the value of each option.

.. code-block:: text

   annunciator check-config PATH

``verify``
~~~~~~~~~~

Examines the integrity data of a JSON Lines log file.

.. code-block:: text

   annunciator verify PATH [--key-env NAME] [--expected-start HASH]

.. list-table:: Options of the command ``verify``
   :name: tab-cli-verify
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--key-env NAME``
     - The environment variable that contains the key. The default is
       ``ANNUNCIATOR_CHAIN_KEY``.
   * - ``--expected-start HASH``
     - The last hash of the older file. Use this option for a file after
       a rotation.

``diff``
~~~~~~~~

Compares the events of two JSON Lines log files.

.. code-block:: text

   annunciator diff FIRST SECOND [--json]

``FIRST`` is the reference run. ``SECOND`` is the run to examine. The
option ``--json`` writes the comparison as a JSON object.

``lint``
~~~~~~~~

Examines the message codes in Python source files. Use the general option
``--import`` to load your catalogue.

.. code-block:: text

   annunciator lint PATH [PATH ...] [--prefix PREFIX] [--no-unused] [--strict]

.. list-table:: Options of the command ``lint``
   :name: tab-cli-lint
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--prefix PREFIX``
     - Examines only the catalogue with this prefix. You can give this
       option more than one time.
   * - ``--no-unused``
     - Does not show the codes that the source code does not use.
   * - ``--strict``
     - Gives the exit status 1 for unused codes also.

``demo``
~~~~~~~~

Shows one example event of each severity and one event with a code.

.. code-block:: text

   annunciator demo

Selection options
-----------------

The commands ``report`` and ``view`` accept the selection options. An event
must agree with all given options.

.. list-table:: Selection options
   :name: tab-cli-selection
   :widths: 35 65
   :header-rows: 1

   * - Option
     - Function
   * - ``--min-severity SEVERITY``
     - Selects the events of this severity or higher.
   * - ``--code PATTERN``
     - Selects the events with a code that agrees with the pattern, for
       example ``"APP-E-*"``.
   * - ``--logger PATTERN``
     - Selects the events with a logger name that agrees with the pattern.
   * - ``--text TEXT``
     - Selects the events that contain this text in the message.
   * - ``--fingerprint TEXT``
     - Selects the events of the failure that has this fingerprint.

In a pattern, ``*`` agrees with all characters and ``?`` agrees with one
character. Put a pattern in quotation marks.

Exit status
-----------

.. list-table:: Exit status of the command-line interface
   :name: tab-cli-exit
   :widths: 15 85
   :header-rows: 1

   * - Status
     - Meaning
   * - 0
     - The command completed. For ``report``: the log has no errors. For
       ``verify``, ``diff`` and ``lint``: the command found no problem.
   * - 1
     - For ``report``: the worst severity in the selected events is
       ``ERROR``. For ``verify``: the integrity check failed. For
       ``diff``: the second run has new problems. For ``lint``: the
       source code has incorrect codes.
   * - 2
     - For ``report``: the worst severity in the selected events is
       ``CRITICAL``.
   * - 64
     - The command line is not correct.
   * - 66
     - The interface cannot import a module or cannot read a file.
   * - Other
     - The exit status of the coded error that stopped the command. Refer
       to :numref:`tab-exit-codes`.

.. note::

   You can use the exit status of ``report`` in a script to stop a
   sequence of steps when a run had errors.
