.. index:: conformity, ISO/IEC/IEEE 26514, ASD-STE100

Conformity to standards
=======================

This chapter tells you how the manual applies the two standards in
:numref:`tab-standards`. It also gives the limits of the conformity
statement.

Structure and content: ISO/IEC/IEEE 26514:2022
----------------------------------------------

:numref:`tab-26514` shows where the manual gives each information
component that the standard defines for information for users.

.. list-table:: Information components and their position in this manual
   :name: tab-26514
   :class: longtable
   :widths: 40 60
   :header-rows: 1

   * - Component
     - Position
   * - Identification data
     - Title page and :doc:`identification`
   * - Table of contents
     - Contents list on the first page. Navigation panel in the HTML form.
   * - List of illustrations
     - List of figures and list of tables in the PDF form. All figures and
       tables have a number and a title.
   * - Introduction
     - First page and :doc:`about`
   * - Information for use of the documentation
     - :doc:`about`
   * - Concept of operations
     - :doc:`concept`
   * - Procedures
     - :doc:`installation` and :doc:`procedures`
   * - Information on software commands
     - :doc:`ref_cli`, :doc:`ref_configuration` and :doc:`ref_api`
   * - Error messages and problem resolution
     - :doc:`messages`
   * - Critical information (warnings, cautions, notes)
     - Definitions in :doc:`about`. Each caution and note is immediately
       before the step or the text that it applies to.
   * - Glossary
     - :doc:`glossary`
   * - Related information sources
     - :doc:`related`
   * - Navigational features
     - Section numbers, cross-references, numbered figures and tables.
       Links to the previous page and the subsequent page in the HTML
       form.
   * - Index
     - General index in the two forms
   * - Search capability
     - Search function in the HTML form. Text search in the PDF form.

The manual also applies these principles of the standard:

* The procedures are task-oriented. Each procedure has a purpose,
  initial conditions, numbered steps and a result.
* The reference data are separate from the procedures.
* The same term always has the same meaning. :doc:`glossary` defines the
  terms.
* The message reference comes directly from the software. Thus the manual
  and the software agree.

Language: ASD-STE100 Issue 9
----------------------------

The text of the manual applies the writing rules of the specification.
:numref:`tab-ste` gives the primary rules and their application.

.. list-table:: Application of the writing rules
   :name: tab-ste
   :widths: 40 60
   :header-rows: 1

   * - Rule
     - Application in this manual
   * - Use approved words with their approved meanings.
     - Applied. Technical names and technical verbs are in
       :numref:`tab-technical-names` and :numref:`tab-technical-verbs`.
   * - Keep procedural sentences to a maximum of 20 words.
     - Applied. The tool ``ste_check.py`` counts the words.
   * - Keep descriptive sentences to a maximum of 25 words.
     - Applied. The tool ``ste_check.py`` counts the words.
   * - Keep paragraphs to a maximum of 6 sentences.
     - Applied. The tool ``ste_check.py`` counts the sentences.
   * - Write only one instruction in each step.
     - Applied, unless two actions occur at the same time.
   * - Write instructions in the imperative form.
     - Applied in all numbered steps.
   * - Use the active voice.
     - Applied in procedures. Applied in descriptive text where possible.
   * - Do not make noun clusters of more than three nouns.
     - Applied, with the exception of technical names.
   * - Use a vertical list for complex text.
     - Applied.
   * - Start a caution with a clear command or condition.
     - Applied.

The documentation text in the source code applies the same rules. That
text is the source of :doc:`ref_api`.

Limits of the conformity statement
----------------------------------

.. note::

   The author applied the two standards during the preparation of this
   manual. An independent organisation did not examine the manual.

These limits apply:

* The tool ``ste_check.py`` examines sentence length, paragraph length,
  contractions and a list of words that are not approved. It does not
  contain the full dictionary of the specification.
* The tool cannot examine the meaning of a word or the voice of a
  sentence. A person must examine these items.
* Text that comes from other software is not in Simplified Technical
  English. Examples are Python tracebacks and the names in program code.
* The licence text in the file ``LICENSE`` is a legal text. The writing
  rules do not apply to it.

If your organisation must show formal conformity, a qualified person must
examine the manual against the two standards.
