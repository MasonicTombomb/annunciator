.. index:: run; procedure, manifest; procedure, integrity; procedure,
   tamper-evident log, comparison of runs

Record and compare runs
=======================

.. rubric:: Purpose

To record the data that are necessary to do a run again. Also to show
that a log file did not change and to compare two runs.

.. rubric:: Before you start

Configure a log file with the option ``file_format`` set to ``"json"``.
Refer to :doc:`proc_configure`.

Record the manifest of a run
----------------------------

.. rubric:: Procedure

1. Put the code of the run in a ``with start_run(...)`` block.
2. Give the names of the packages that have an effect on the result.
3. Give the seed of the random number generator and the parameters of the
   run:

   .. code-block:: python
      :caption: A run with a manifest
      :name: ex-run

      import random
      import sys

      from annunciator import configure, start_run

      configure(file="logs/run.jsonl", file_format="json")

      seed = 20261112
      random.seed(seed)
      with start_run("depletion", packages=("numpy", "scipy"), seed=seed,
                     cooling_time=3.0, burnup=45.0) as run:
          calculate()
          run.save_manifest("logs/run_manifest.json")
      sys.exit(run.exit_code)

.. rubric:: Result

The log contains ``ANN-N-0401`` at the start of the run. The field
``manifest`` of that event contains the items in :numref:`tab-manifest`.
At the end, the log contains ``ANN-N-0402`` with the duration and the
number of errors and warnings. If an exception stops the run, the log
contains ``ANN-E-0403``.

All events of the run have the context field ``run_id``.

.. note::

   The function records the seed. It does not set the seed. Step 3 shows
   how to set it.

.. note::

   The manifest does not contain the name of the user by default. To
   include it, set the parameter ``include_user`` to ``True``.

Make a tamper-evident log file
------------------------------

Use this procedure when a log file is a record that other persons must
trust.

.. rubric:: Procedure

1. Set the option ``file_chain`` to true:

   .. code-block:: python

      configure(file="logs/run.jsonl", file_format="json", file_chain=True)

2. For protection against a person who can write the file, set a key. Put
   the key in the environment variable ``ANNUNCIATOR_CHAIN_KEY`` before
   you start the program.
3. Run the program.
4. After the run, record the last hash in a different location. The
   command in the subsequent procedure shows the sequence numbers.

.. rubric:: Result

Each record of the log file contains the object ``chain``. The object
contains a sequence number, the hash of the record before it and its own
hash.

.. caution::

   Without a key, a person who can write the file can also calculate a new
   chain. Use a key and keep it in a location that the person cannot read.

.. caution::

   The chain cannot show that a person removed the last records of a file.
   To find that, compare the last sequence number with your record from
   step 4.

Examine the integrity of a log file
-----------------------------------

.. rubric:: Procedure

1. If the program used a key, set the environment variable
   ``ANNUNCIATOR_CHAIN_KEY`` to the same key.
2. Do this command:

   .. code-block:: console

      annunciator verify logs/run.jsonl

3. Read the result.

.. rubric:: Result

If the file is complete and did not change, the command shows this text
and the exit status is 0:

.. code-block:: text

   The integrity check passed: logs/run.jsonl
   Records: 47 (sequence 1 to 47)

If a record changed or is absent, the command shows the line number of each
problem. The exit status is 1:

.. code-block:: text

   The integrity check FAILED: logs/run.jsonl
     line 6: the contents were changed
     line 9: sequence number 10, expected 9

.. note::

   After a rotation, the new file continues the chain of the old file.
   Then the first sequence number is more than 1. Examine the old file
   also.

Compare two runs
----------------

.. rubric:: Procedure

1. Keep the log file of a run that had a correct result. This file is the
   reference.
2. Compare the log file of the new run with the reference:

   .. code-block:: console

      annunciator diff logs/reference.jsonl logs/run.jsonl

.. rubric:: Result

The command shows the message codes and the failures that are different:

.. code-block:: text

   Severity counts (first run -> second run):
     ERROR    1 -> 3
   Message codes with different counts:
     ANN-E-0303       1 -> 3
   New failures in the second run:
     46c1ff9f2e2a  IndexError: list index out of range
   Result: the second run has new problems.

The exit status is 1 if the second run has a new failure or a new code of
the severity ``WARNING`` or higher. If not, the exit status is 0.

In a program, the function ``compare_runs`` gives the same data.
