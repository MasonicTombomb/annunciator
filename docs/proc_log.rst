.. index:: logger; procedure, structured fields, context; procedure, redaction

Record events
=============

.. rubric:: Purpose

To record information, warnings and errors with structured fields and
context data.

.. rubric:: Before you start

Configure the library. Refer to :doc:`proc_configure`.

Record a message
----------------

.. rubric:: Procedure

1. Get a logger in each module. Use the name of the module:

   .. code-block:: python

      from annunciator import get_logger

      log = get_logger(__name__)

2. Call the method that has the name of the severity. Give the data as
   keyword arguments:

   .. code-block:: python
      :caption: Messages with structured fields
      :name: ex-log

      log.debug("The spectrum has %d channels.", 8192)
      log.info("The fit completed.", chi_square=1.07, iterations=14)
      log.notice("The calibration is complete.")
      log.warning("The peak is near the edge of the range.", channel=8101)
      log.error("The file is not available.", path="run_17.spe")
      log.critical("The detector lost its high voltage.")

3. In an ``except`` block, use ``exception`` or ``report`` to record the
   traceback:

   .. code-block:: python

      try:
          spectrum = load("run_17.spe")
      except OSError as error:
          log.report(error, operation="load spectrum", path="run_17.spe")
          raise

.. rubric:: Result

Each call makes one event. The keyword arguments are the structured fields
of the event. In a JSON Lines file, the fields are in the object
``fields``.

.. note::

   Put values in fields, not in the message text. Then the message text
   stays constant and you can find all events of one type.

Add context data
----------------

Context data are fields that the library adds to all events of one
operation.

.. rubric:: Procedure

1. To add data for a block of code, use the context manager ``context``:

   .. code-block:: python
      :caption: Context data
      :name: ex-context

      from annunciator import context, get_logger

      log = get_logger(__name__)

      with context(run="R-17", sample="CeO2-04"):
          log.info("The acquisition started.")
          acquire()
          log.info("The acquisition stopped.")

2. To add data until the end of the thread or the task, use ``bind``:

   .. code-block:: python

      from annunciator import bind, new_correlation_id

      bind(operator="T. Scott")
      new_correlation_id()

3. To give permanent fields to one logger, use the method ``bind`` of the
   logger:

   .. code-block:: python

      detector_log = log.bind(detector="HPGe-2")
      detector_log.info("The bias is stable.")

.. rubric:: Result

All events in the block of step 1 have the fields ``run`` and ``sample``.
Events from functions that the block calls also have these fields.

Keep secret data out of the log
-------------------------------

.. caution::

   Do not put secret data in the message text. The redaction filter
   replaces the values of fields that have secret names. It examines the
   message text only for the patterns that you supply.

.. rubric:: Procedure

1. Give secret values in fields that have a secret name. Examples are
   ``password`` and ``api_token``:

   .. code-block:: python

      log.info("The connection is open.", user="tom", api_token=token)

2. If your secret fields have other names, add the names to the option
   ``redact_keys``.
3. If secret text can occur in messages, add a regular expression to the
   option ``redact_patterns``:

   .. code-block:: python

      configure(redact_patterns=(r"sk-[A-Za-z0-9]{20,}",))

.. rubric:: Result

The log shows ``[REDACTED]`` as a replacement for each secret value.
:numref:`tab-options-filters` gives the default key names.
