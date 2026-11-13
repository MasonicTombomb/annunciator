.. index:: message catalogue; procedure, message code; procedure

Define a message catalogue
==========================

.. rubric:: Purpose

To give a code, a probable cause and a remedy to each message of your
program.

.. rubric:: Before you start

* Read :ref:`the description of message codes <fig-code>` in
  :doc:`concept`.
* Select a prefix for your catalogue. The prefix has two to eight capital
  letters or digits. The prefix ``ANN`` is not available, because the
  library uses it.

Define the messages in a module
-------------------------------

.. rubric:: Procedure

1. Make a module for the messages, for example ``myapp/messages.py``.
2. Make the catalogue and define each message:

   .. code-block:: python
      :caption: A message catalogue
      :name: ex-catalogue

      from annunciator import MessageCatalogue

      APP = MessageCatalogue("APP", "Messages of the spectrum tools")

      APP.define(
          1, "E", "The detector '{name}' does not answer.",
          cause="The detector has no power or the cable is not connected.",
          remedy="Make sure that the detector has power. Examine the cable.",
          category="Hardware",
      )
      APP.define(
          2, "W", "The dead time is {dead_time} %.",
          cause="The count rate is too high for the detector.",
          remedy="Increase the distance between the source and the detector.",
          category="Measurement",
      )
      APP.define(
          3, "I", "The run '{run}' completed. Live time: {live_time} s.",
      )

3. Import the module before the program uses a code. Usually, import it in
   the file ``__init__.py`` of your package.

.. rubric:: Result

The command that follows shows your three messages:

.. code-block:: console

   annunciator --import myapp.messages catalogue --prefix APP

.. note::

   Write the message text as a full sentence. Write the cause as a
   statement. Write the remedy as an instruction.

Record a message from the catalogue
-----------------------------------

.. rubric:: Procedure

1. Call the method ``event`` of a logger. Give the code and the values for
   the replacement fields:

   .. code-block:: python

      from annunciator import get_logger

      log = get_logger(__name__)
      log.event("APP-W-0002", dead_time=31)
      log.event("APP-I-0003", run="R-17", live_time=600)

.. rubric:: Result

The logger gets the severity and the text from the definition. For the
severity ``WARNING`` and higher, the plain text shows the cause and the
remedy:

.. code-block:: text

   2026-11-12T10:15:02.454Z WARNING  myapp.daq [APP-W-0002] The dead time is 31 %. | dead_time=31
       Cause:  The count rate is too high for the detector.
       Remedy: Increase the distance between the source and the detector.

.. note::

   If the code has no definition, the logger records an ``ERROR`` event
   that contains the code and the fields. It does not raise an exception.
   To get an exception in your tests, set the parameter ``strict`` to
   ``True``.

Keep the catalogue in a file
----------------------------

Use this procedure when persons who do not write Python must change the
message texts.

.. rubric:: Procedure

1. Write the catalogue to a JSON file one time:

   .. code-block:: python

      APP.save("messages.json")

2. Change the texts in the file with a text editor.
3. In the program, read the file as a replacement for the calls of
   ``define``:

   .. code-block:: python

      from annunciator import MessageCatalogue

      APP = MessageCatalogue.load("messages.json")

.. rubric:: Result

The program uses the texts of the file. :doc:`ref_formats` gives the
structure of the file.

Show the definition of a code
-----------------------------

.. rubric:: Procedure

1. In a terminal, give the code to the command ``explain``:

   .. code-block:: console

      annunciator --import myapp.messages explain APP-E-0001

.. rubric:: Result

The terminal shows the severity, the message text, the cause and the
remedy of the code.
