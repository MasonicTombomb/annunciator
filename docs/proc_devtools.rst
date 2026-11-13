.. index:: lint; procedure, tests; procedure, pytest, HTML report; procedure

Examine your code and share results
===================================

.. rubric:: Purpose

To find incorrect message codes before a run, to examine events in tests,
and to give a readable report of a run to other persons.

Examine the message codes in your source code
---------------------------------------------

.. rubric:: Before you start

Define a message catalogue in a module. Refer to :doc:`proc_catalogue`.

.. rubric:: Procedure

1. Do the command ``lint``. Give the module that defines the catalogue and
   the directory of your source code:

   .. code-block:: console

      annunciator --import myapp.messages lint src/myapp

2. Correct each finding of the types ``undefined`` and ``missing-field``.
3. Examine each finding of the type ``unused``. Remove the definition if
   the message is no longer necessary.
4. Do step 1 again.

.. rubric:: Result

The command shows one line for each finding. :numref:`tab-lint` gives the
types. The exit status is 1 if the command found an ``undefined`` or a
``missing-field`` problem.

.. code-block:: text

   src/myapp/daq.py:41: undefined: APP-E-0012
   src/myapp/daq.py:57: missing-field: APP-E-0001 (no value for: name)
   unused: APP-W-0007 (The buffer is {fill} % full.)
   3 findings, 2 errors

.. list-table:: Types of findings of the command ``lint``
   :name: tab-lint
   :widths: 20 80
   :header-rows: 1

   * - Type
     - Meaning
   * - ``undefined``
     - The source code uses a code that has no definition. At run time,
       the message has no text, no cause and no remedy.
   * - ``missing-field``
     - A call gives a code but gives no value for a replacement field. At
       run time, the message shows the field name in braces.
   * - ``unused``
     - A catalogue defines a code that the source code does not use.

.. note::

   The command reads the source code. It does not run it. It cannot find
   a code that the program makes at run time.

.. note::

   Add this command to the automatic checks of your project. Then an
   incorrect code cannot go into a release.

Examine events in a test
------------------------

.. rubric:: Procedure

1. If you use pytest, add the fixture ``annunciator_events`` to the
   arguments of the test function. No import is necessary.
2. Call the code that you must examine.
3. Call ``assert_logged`` or ``assert_not_logged`` with the conditions:

   .. code-block:: python
      :caption: A test with the pytest fixture
      :name: ex-pytest

      def test_high_dead_time_gives_warning(annunciator_events):
          measure(dead_time=45)

          event = annunciator_events.assert_logged("APP-W-0002", count=1)
          assert event.fields["dead_time"] == 45
          annunciator_events.assert_not_logged(minimum="ERROR")

4. If you do not use pytest, use the context manager ``capture_events``:

   .. code-block:: python

      from annunciator.testing import capture_events

      with capture_events() as captured:
          measure(dead_time=45)
      captured.assert_logged("APP-W-0002")

.. rubric:: Result

The test fails if the necessary event is absent or if a forbidden event
occurred. The failure text shows the last 20 recorded events.

.. list-table:: Conditions of ``assert_logged`` and ``assert_not_logged``
   :name: tab-assert
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Condition
   * - ``code``
     - The event has this message code.
   * - ``severity``
     - The event has this severity.
   * - ``minimum``
     - The event has this severity or higher.
   * - ``text``
     - The message contains this text.
   * - ``logger``
     - The event comes from the logger with this name.
   * - ``count``
     - For ``assert_logged`` only: the number of events that must agree.
   * - Other keywords
     - The event has a structured field with this name and this value.

Make an HTML report of a run
----------------------------

.. rubric:: Procedure

1. Do the command ``report`` with the option ``--html``:

   .. code-block:: console

      annunciator report logs/run.jsonl --html run_report.html --title "Run R-17"

2. Open the file ``run_report.html`` in a browser.

.. rubric:: Result

The page has the style of a printed industrial report. It has a title
block, four numbered sections and ruled tables in a fixed-width font. It
does not use colour. An asterisk identifies each error.

.. list-table:: Sections of the HTML report
   :name: tab-html-sections
   :widths: 35 65
   :header-rows: 1

   * - Section
     - Contents
   * - Title block
     - The title, the date of issue, the number of events, the worst
       severity and the period of the record.
   * - 1. Summary by severity
     - The number of events for each severity.
   * - 2. Summary by message code
     - The number of events for each message code.
   * - 3. Distinct failures
     - One line for each fingerprint.
   * - 4. Event log
     - One line for each event, with its number in the log.

On the page, you can do these actions:

* Click a severity to show or hide its events.
* Click a message code or a failure to show only its events.
* Type text in the field ``FIND`` to find events.
* Click an event to show its fields, cause, remedy and traceback.
* Click ``EXPAND ALL`` to show these data for all listed events.
* Click ``PRINT`` to print the report. The printed report does not show
  the controls.

The file has no external parts. You can send it to other persons and they
can open it without a network connection.

.. caution::

   The HTML file contains the full data of the events. Make sure that it
   contains no secret data before you send it.

In a program, the function ``write_html_report`` writes the same file.
