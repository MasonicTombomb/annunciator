.. index:: coded error; reference, coded warning; reference, exit status; reference

Error classes and warning classes
=================================

Coded errors
------------

:numref:`tab-exit-codes` gives the classes of coded errors.
:numref:`fig-hierarchy` shows the relations between the classes. The exit
status values agree with the usual values of the file ``sysexits.h``.

.. list-table:: Classes of coded errors
   :name: tab-exit-codes
   :class: longtable
   :widths: 30 10 18 42
   :header-rows: 1

   * - Class
     - Exit status
     - Default code
     - Use
   * - ``CodedError``
     - 1
     - None
     - Base class. Use it when no other class agrees.
   * - ``ConfigurationError``
     - 78
     - None
     - A configuration value or file is not correct.
   * - ``ValidationError``
     - 65
     - None
     - An input value is not correct. Also a ``ValueError``.
   * - ``DataError``
     - 65
     - None
     - The contents of a data set are not correct.
   * - ``ResourceError``
     - 74
     - None
     - A file, a device or a network resource caused an error.
   * - ``ResourceNotFoundError``
     - 66
     - None
     - A necessary resource does not exist.
   * - ``ResourceAccessError``
     - 77
     - None
     - The program does not have access to a resource.
   * - ``OperationError``
     - 1
     - None
     - An operation did not complete.
   * - ``OperationTimeoutError``
     - 75
     - ``ANN-E-0310``
     - An operation did not complete in the permitted time.
   * - ``RetryExhaustedError``
     - 75
     - ``ANN-E-0302``
     - All attempts of an operation failed.
   * - ``DependencyError``
     - 69
     - None
     - A necessary package, program or service is not available.
   * - ``InternalError``
     - 70
     - None
     - The program found a defect in its own logic. The severity is
       ``CRITICAL``.
   * - ``CatalogueError``
     - 70
     - None
     - A message code or a catalogue is not correct.
   * - ``AggregateError``
     - 1
     - ``ANN-E-0304``
     - A group of errors from an ``ErrorCollector``.

Attributes of a coded error
---------------------------

.. list-table:: Attributes of coded errors and coded warnings
   :name: tab-error-attributes
   :widths: 20 20 60
   :header-rows: 1

   * - Attribute
     - Type
     - Contents
   * - ``code``
     - ``str`` or ``None``
     - The message code.
   * - ``message``
     - ``str``
     - The message text with the field values.
   * - ``severity``
     - ``Severity``
     - The severity of the definition, or the default of the class.
   * - ``cause``
     - ``str``
     - The probable cause.
   * - ``remedy``
     - ``str``
     - The corrective action.
   * - ``fields``
     - ``dict``
     - The values of the replacement fields.
   * - ``context``
     - ``dict``
     - More data about the conditions.

.. note::

   The attribute ``cause`` is a text for the user. The attribute
   ``__cause__`` is the initial exception of a ``raise ... from``
   statement.

Coded warnings
--------------

.. list-table:: Classes of coded warnings
   :name: tab-warning-classes
   :widths: 32 18 50
   :header-rows: 1

   * - Class
     - Default code
     - Use
   * - ``CodedWarning``
     - None
     - Base class. A subclass of ``UserWarning``.
   * - ``ConfigurationWarning``
     - None
     - A configuration value is permitted but is possibly not correct.
   * - ``DataQualityWarning``
     - None
     - The quality of the input data can cause an incorrect result.
   * - ``PerformanceWarning``
     - None
     - An operation is slow or uses much memory.
   * - ``DeprecatedFeatureWarning``
     - ``ANN-W-0309``
     - The program uses a feature that a future version will remove. Also
       a ``DeprecationWarning``.
