.. index:: severity; reference, level

Severities
==========

:numref:`tab-severity` gives the seven severities. The numeric values agree
with the levels of the standard ``logging`` module. ``TRACE`` and ``NOTICE``
are additions of this library.

.. list-table:: Severities
   :name: tab-severity
   :widths: 14 8 8 14 56
   :header-rows: 1

   * - Name
     - Value
     - Letter
     - Log method
     - When to use
   * - ``TRACE``
     - 5
     - T
     - ``trace``
     - Very detailed data, for example each step of a loop.
   * - ``DEBUG``
     - 10
     - D
     - ``debug``
     - Data that helps a developer to find the cause of a fault.
   * - ``INFO``
     - 20
     - I
     - ``info``
     - Normal progress of the program.
   * - ``NOTICE``
     - 25
     - N
     - ``notice``
     - A normal event that is important to the user, for example the end
       of a run.
   * - ``WARNING``
     - 30
     - W
     - ``warning``
     - The program continues, but a result is possibly incorrect.
   * - ``ERROR``
     - 40
     - E
     - ``error``
     - An operation did not complete.
   * - ``CRITICAL``
     - 50
     - C
     - ``critical``
     - The program cannot continue.

You can give a severity in four forms. All forms have the same effect:

* a member of the class ``Severity``, for example ``Severity.WARNING``,
* a name, for example ``"WARNING"`` or ``"warning"``,
* a letter, for example ``"W"``,
* a number, for example ``30``.

The names ``WARN``, ``ERR`` and ``FATAL`` are also permitted. They select
``WARNING``, ``ERROR`` and ``CRITICAL``.

With the default configuration, the console shows the severities ``TRACE``
to ``NOTICE`` on ``stdout``. It shows ``WARNING`` to ``CRITICAL`` on
``stderr``.
