.. index:: document identification, change record

Document identification
=======================

Identification data
-------------------

.. list-table:: Identification data of this manual
   :name: tab-identification
   :widths: 30 70
   :header-rows: 1

   * - Item
     - Value
   * - Title
     - annunciator User Manual
   * - Document number
     - |docnum|
   * - Issue
     - |issue|
   * - Issue date
     - |date|
   * - Applicable software
     - annunciator, version |release|
   * - Applicable environment
     - Python 3.9 or later on Windows, Linux and macOS
   * - Author and issuer
     - Tom Scott
   * - Licence of the software
     - MIT licence
   * - Language
     - English (ASD-STE100 Simplified Technical English, Issue 9)

Change record
-------------

.. list-table:: Change record
   :name: tab-changes
   :widths: 10 20 20 50
   :header-rows: 1

   * - Issue
     - Date
     - Software version
     - Change
   * - 1
     - 2026-11-12
     - 1.0.0
     - First issue.
   * - 2
     - 2026-11-12
     - 1.1.0
     - Added four procedures: :doc:`proc_longrun`, :doc:`proc_runs`,
       :doc:`proc_robust` and :doc:`proc_devtools`. Added the related
       options, commands, formats, messages and terms.
   * - 3
     - 2026-11-13
     - 1.1.1
     - Changed the description of the HTML report in
       :doc:`proc_devtools`. The report now has the style of a printed
       industrial report.

Applicability
-------------

This issue applies only to version |release| of the software. To find the
version of your software, do this command:

.. code-block:: console

   annunciator --version

If the version is different, use the issue of the manual that applies to
your version.

Copyright and restrictions
--------------------------

Copyright 2026, Tom Scott. The MIT licence applies to the software and to
this manual. The file ``LICENSE`` in the software package contains the text
of the licence.

The software has no warranty. The licence text gives the conditions.

Forms of this manual
--------------------

The manual is available in two forms. The two forms have the same contents.

* The HTML form is for use on a screen. It has a navigation panel, a search
  function and an index.
* The PDF form is for a printed copy. It has a table of contents, a list of
  figures, a list of tables and an index.
