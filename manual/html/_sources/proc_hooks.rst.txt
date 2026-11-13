.. index:: hooks; procedure, unhandled exception, thread, asyncio

Record unhandled exceptions
===========================

.. rubric:: Purpose

To make sure that the log contains each exception that stops the program
or a thread.

.. rubric:: Before you start

The function ``configure`` installs the hooks by default. Do this
procedure only in these conditions:

* you set the option ``install_hooks`` to ``False``, or
* you do not use ``configure``, or
* your program uses ``asyncio``.

Install the hooks
-----------------

.. rubric:: Procedure

1. Call ``install_hooks`` one time, near the start of the program:

   .. code-block:: python

      from annunciator import install_hooks

      install_hooks()

2. To remove the hooks, call ``uninstall_hooks``.

.. rubric:: Result

:numref:`tab-hooks` gives the events that the hooks record.

.. list-table:: Events of the hooks
   :name: tab-hooks
   :widths: 45 20 35
   :header-rows: 1

   * - Condition
     - Code
     - Logger
   * - An exception stops the program
     - ``ANN-C-0201``
     - ``annunciator.hooks``
   * - An exception stops a thread
     - ``ANN-C-0202``
     - ``annunciator.hooks``
   * - Python cannot raise an exception
     - ``ANN-E-0204``
     - ``annunciator.hooks``
   * - A module issues a Python warning
     - ``ANN-W-0205``
     - ``py.warnings``

A coded error keeps its own code. The hook records it with the severity
``CRITICAL`` and the field ``uncaught``.

.. note::

   The hooks do not record ``KeyboardInterrupt`` and ``SystemExit``.
   These exceptions are a normal stop of the program.

Record the errors of an ``asyncio`` event loop
----------------------------------------------

.. rubric:: Procedure

1. In the first coroutine of the program, call
   ``install_asyncio_handler``:

   .. code-block:: python

      import asyncio

      from annunciator import configure, install_asyncio_handler

      async def main():
          install_asyncio_handler()
          await run_tasks()

      configure()
      asyncio.run(main())

.. rubric:: Result

When a task raises an exception and no code awaits the task, the log
contains an event with the code ``ANN-E-0203``.
