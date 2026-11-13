.. index:: configuration; procedure, log file, rotation, environment variable

Configure the library
=====================

.. rubric:: Purpose

To select the minimum severity, the destinations and the formats of the
events.

.. rubric:: Before you start

Read :doc:`ref_configuration`. It gives all options and their permitted
values.

Configure the library in the program
------------------------------------

.. rubric:: Procedure

1. Import the function ``configure``.
2. Call the function one time, near the start of the program. Give the
   options as keyword arguments:

   .. code-block:: python
      :caption: Configuration in the program
      :name: ex-configure

      from annunciator import configure

      configure(
          level="DEBUG",
          console_level="INFO",
          file="logs/run.jsonl",
          file_format="json",
          rotate="size",
          max_bytes=5_000_000,
          backup_count=3,
      )

3. To change the configuration, call ``configure`` again with the new
   options.

.. rubric:: Result

The console shows events of the severity ``INFO`` and higher. The file
``logs/run.jsonl`` contains events of the severity ``DEBUG`` and higher,
one JSON object on each line. The library makes the directory ``logs`` if
it does not exist.

.. note::

   A second call of ``configure`` removes the handlers of the first call.
   It does not remove handlers that other code installed.

Configure the library from a file
---------------------------------

.. rubric:: Procedure

1. Make a TOML file, for example ``annunciator.toml``:

   .. code-block:: toml
      :caption: Configuration file
      :name: ex-toml

      [annunciator]
      level = "INFO"
      file = "logs/run.log"
      rotate = "time"
      when = "midnight"
      backup_count = 14
      duplicate_window = 10.0

      [annunciator.logger_levels]
      "matplotlib" = "WARNING"

2. Examine the file:

   .. code-block:: console

      annunciator check-config annunciator.toml

3. If the command shows a message code, refer to :doc:`messages`. Correct
   the file and do step 2 again.
4. Give the path of the file to ``configure``:

   .. code-block:: python

      from annunciator import configure

      configure("annunciator.toml")

.. rubric:: Result

Step 2 shows the text ``The configuration file is correct`` and the value
of each option. The program then uses these values.

.. note::

   You can also put the options in the table ``[tool.annunciator]`` of the
   file ``pyproject.toml``.

Configure the library from the environment
------------------------------------------

Use this procedure to change an option for one run without a change to the
program.

.. rubric:: Procedure

1. In the program, read the environment before you call ``configure``:

   .. code-block:: python

      from annunciator import LogConfig, configure

      base = LogConfig(level="INFO", file="logs/run.log")
      configure(LogConfig.from_env(base=base))

2. In the terminal, set a variable. The name is ``ANNUNCIATOR_`` and the
   option name in capital letters.

   On Windows (PowerShell):

   .. code-block:: console

      $env:ANNUNCIATOR_LEVEL = "DEBUG"

   On Linux and macOS:

   .. code-block:: console

      export ANNUNCIATOR_LEVEL=DEBUG

3. Run the program.

.. rubric:: Result

The program uses the value of the variable for the option ``level``. It
uses the values of ``base`` for all other options.

Stop the library
----------------

.. rubric:: Procedure

1. At the end of the program, call ``shutdown``:

   .. code-block:: python

      from annunciator import shutdown

      shutdown()

.. rubric:: Result

The library writes all records, closes the log file and removes its
handlers and hooks.

.. note::

   The library also calls ``shutdown`` automatically when Python stops.
