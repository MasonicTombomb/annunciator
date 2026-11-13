.. index:: Sphinx extension; procedure, message reference

Document your messages with Sphinx
==================================

.. rubric:: Purpose

To write the message reference of your own manual automatically from your
message catalogue. This manual uses the same procedure for
:doc:`messages`.

.. rubric:: Before you start

* Define a message catalogue in a module. Refer to :doc:`proc_catalogue`.
* Make a Sphinx project for your manual.
* Make sure that Sphinx can import your package.

.. rubric:: Procedure

1. Open the file ``conf.py`` of your Sphinx project.
2. Add the extension to the list ``extensions``:

   .. code-block:: python

      extensions = [
          "annunciator.sphinxext",
      ]

3. In a page of your manual, add the directive. Give the prefix of the
   catalogue and the module that defines it:

   .. code-block:: rst
      :caption: Directive for a message reference
      :name: ex-directive

      Messages
      ========

      .. annunciator-catalogue:: APP
         :module: myapp.messages
         :min-severity: WARNING

4. To refer to one message in your text, use the role ``msg``:

   .. code-block:: rst

      If the detector has no power, the program shows :msg:`APP-E-0001`.

5. Build the manual.

.. rubric:: Result

The page contains one section for each message. Each section shows the
severity, the message text, the cause and the remedy. Each code is in the
index. The role ``msg`` makes a link to the section of the code.

.. note::

   The options ``min-severity`` and ``category`` are optional. Without
   them, the directive writes all messages of the catalogue.
