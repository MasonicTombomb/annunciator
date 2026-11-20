.. index:: installation, upgrade, removal, necessary software

Installation
============

Necessary software
------------------

.. list-table:: Necessary software
   :name: tab-requirements
   :widths: 30 70
   :header-rows: 1

   * - Item
     - Necessary condition
   * - Python
     - Version 3.9 or later
   * - Operating system
     - Windows, Linux or macOS
   * - Other packages
     - None for the library. Python 3.9 and 3.10 must have the package
       ``tomli`` to read TOML files.
   * - To do the tests
     - The package ``pytest``, version 7 or later.
   * - To build this manual
     - The packages ``sphinx`` and ``furo``. A LaTeX system is necessary for
       the PDF form.

Install the library
-------------------

.. rubric:: Purpose

To install the library in your Python environment.

.. rubric:: Before you start

* Make sure that Python 3.9 or later is installed.
* Make sure that the computer can connect to the Python Package Index
  (PyPI). If it cannot connect, get the software package ``annunciator``.
  The package is a directory or a ``.whl`` file.

.. rubric:: Procedure

1. Open a terminal.
2. If you use a virtual environment or a conda environment, activate it.
3. Install the library from PyPI:

   .. code-block:: console

      python -m pip install annunciator

   If you have the software package, go to the directory that contains
   the file ``pyproject.toml`` and do this command:

   .. code-block:: console

      python -m pip install .

   If you have a ``.whl`` file, give the path of the file as a replacement
   for the full stop.

4. If your Python version is 3.9 or 3.10 and you use TOML files, install
   the extra ``toml``:

   .. code-block:: console

      python -m pip install "annunciator[toml]"

.. rubric:: Result

The library is installed. Do the procedure
:ref:`Make sure that the installation is correct <verify-install>`.

.. note::

   You can also use these sources:

   * GitHub. To install a specified version, give its tag, for example
     ``v1.1.4``:

     .. code-block:: console

        python -m pip install "git+https://github.com/MasonicTombomb/annunciator.git@v1.1.4"

   * The conda channel ``MasonicTombomb`` on anaconda.org:

     .. code-block:: console

        conda install -c MasonicTombomb annunciator

.. _verify-install:

Make sure that the installation is correct
------------------------------------------

.. rubric:: Purpose

To make sure that Python can find the library and that the library
operates.

.. rubric:: Procedure

1. Show the version:

   .. code-block:: console

      annunciator --version

2. Show an example of each severity:

   .. code-block:: console

      annunciator demo

.. rubric:: Result

Step 1 shows ``annunciator`` and the version number. Step 2 shows these
lines:

* One line with the code ``ANN-D-0010``. This line shows the configuration
  of the logging.
* Seven lines, one for each severity.
* One line with the code ``ANN-E-0001``, with its cause and its remedy.

If the terminal cannot find the command ``annunciator``, use
``python -m annunciator`` as a replacement. Refer to
:ref:`Problems without a message code <troubleshooting>`.

Install the library for development
-----------------------------------

.. rubric:: Purpose

To install the library in a mode that uses the source files directly. Then
a change in a source file has an immediate effect.

.. rubric:: Procedure

1. Go to the directory that contains the file ``pyproject.toml``.
2. Install the library in the editable mode, with the tools for the
   manual and for the tests:

   .. code-block:: console

      python -m pip install -e ".[docs,test]"

3. Do the tests:

   .. code-block:: console

      python -m pytest

.. rubric:: Result

The command ``python -m pip show annunciator`` shows the path of your
source directory. Step 3 shows that all tests passed.

.. note::

   Some development environments, for example PyCharm, cannot find the
   modules of a library in the default editable mode. If your development
   environment cannot find the modules, use this command in step 2:

   .. code-block:: console

      python -m pip install -e ".[docs,test]" --config-settings editable_mode=compat

Upgrade the library
-------------------

.. rubric:: Procedure

1. Install the new version from PyPI:

   .. code-block:: console

      python -m pip install --upgrade annunciator

   If you have the new software package, go to the directory that
   contains the new file ``pyproject.toml`` and do this command:

   .. code-block:: console

      python -m pip install --upgrade .

2. Read the file ``CHANGELOG.md`` for changes that have an effect on your
   program.

.. rubric:: Result

The command ``annunciator --version`` shows the new version number.

Remove the library
------------------

.. rubric:: Procedure

1. Remove the library:

   .. code-block:: console

      python -m pip uninstall annunciator

2. Type ``y`` when the command asks for confirmation.

.. rubric:: Result

The command ``python -m pip show annunciator`` shows that the package is
not installed.

.. note::

   This procedure does not remove your log files and your configuration
   files.

Build this manual
-----------------

.. rubric:: Before you start

Install the library for development. That procedure installs ``sphinx``
and ``furo``.

.. rubric:: Procedure

1. Go to the directory that contains the file ``pyproject.toml``.
2. Build the HTML form:

   .. code-block:: console

      sphinx-build -b html docs docs/_build/html

3. If you must have the PDF form, build it:

   .. code-block:: console

      sphinx-build -M latexpdf docs docs/_build

   This command uses ``latexmk``, and ``latexmk`` uses Perl. If the
   command fails on Windows, go to the directory ``docs/_build/latex``
   and do these commands:

   .. code-block:: console

      pdflatex ANN-UM-001.tex
      pdflatex ANN-UM-001.tex
      makeindex -s python.ist ANN-UM-001.idx
      pdflatex ANN-UM-001.tex

4. Examine the text against the writing rules:

   .. code-block:: console

      python tools/ste_check.py docs

.. rubric:: Result

The file ``docs/_build/html/index.html`` is the first page of the HTML
form. The file ``docs/_build/latex/ANN-UM-001.pdf`` is the PDF form. Step 4
shows the number of findings.
