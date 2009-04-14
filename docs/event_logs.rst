:mod:`event_logs` -- Event Logs
===============================

..  module:: event_logs
    :synopsis: Pythonic access to Event Logs
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>

Introduction
------------

Each Windows machine comes equipped with an expandable set of event logs
for tracking system- or application-level event information. This module
offers a Pythonic interface to event logs, including iterating over them,
checking their length and accessing them by means of easy monikers, regardless
of what machine they're on.

.. _event_logs:

Event Logs
~~~~~~~~~~

Each Windows system comes with predefined Event Logs called (in the English-language
versions): Application, System, Security. Certain Microsoft applications create
extra ones, but most applications create an event source against the Applications
log.

.. _event_sources:

Event Sources
~~~~~~~~~~~~~

In principal, event sources are key to the way in which event logs work. An
event source represents a DLL and a resource file containing messages, possibly
in multiple languages, possibly containing placeholders for the calling application
to fill in with the name of a file or a user or whatever. It's linked to one of
the event logs (Application, System, etc). When you log an event, you do it via 
an event source handle.

In reality, it's perfectly possible to log an event against an event source
which doesn't exist. You'll get a bit of boilerplate text in the event
message saying that something couldn't be found, but the event will log.
This module allows creation of simple event sources, via the :meth:`EventSource.create`
method and at present forces an event source to exist before a record can
be logged against it.


Exceptions
----------

..  exception:: x_event_logs

    Base of all exceptions in this module; subclass of :exc:`core.x_winsys`

Constants
---------

..  data:: EVENTLOG_READ
..  data:: EVENTLOG_TYPE
..  data:: DEFAULT_LOG_NAME

    "Application", the name of the most commonly-used event log for recording
    user-initiated events.


Functions
----------

Of these functions, the two you're most likely to need are: :func:`event_log`,
which returns an :class:`EventLog` instance corresponding to the named log,
which you can then iterate over; and :func:`log_event`, which logs an event
against a named source.

..  function:: event_logs (computer : string = ".")

    Iterate over each of the event logs on the computer in question, yielding
    an :class:`EventLog` instance corresponding to each one.
    
..  function:: event_log (log)

    Convenience function to return an :class:`EventLog` instance corresponding
    to log: 
    
    * If log is :const:`None`, return :const:`None`
    * If log is an existing :class:`EventLog` instance, return log
    * Otherwise, treat log as a moniker of the form [\\\\computer\\]name
      and return an :class:`EventLog` corresponding to that log on that
      computer.
      
..  function:: event_sources (log_name=DEFAULT_LOG_NAME, computer=".")

    Iterate over the event sources registered against an event log on
    a computer, yield an :class:`EventSource` instance corresponding to
    each one.
    
..  function:: event_source (source)

    Convenience function to return an :class:`EventSource` instance corresponding
    to source:
    
    * If source is :const:`None`, return :const:`None`
    * If source is an existing :class:`EventSource` instance, return source
    * Otherwise, treat source as a moniker of the form [[\\\\computer]\\log\\]name
      and return a :class:`EventSource` corresponding to that source.
      
..  function:: log_event (source, type="error", message=None, data=None, id=0, category=0, principal=core.UNSET)

    Log an event against the source, which implies an event log type. 
    
    :param source: the event source for this event
    :type source: anything accepted by :func:`event_source`
    :param type: whether information or error etc.
    :type type: anything accepted by :data:`EVENTLOG_TYPE`
    :param message: the message associated with the event
    :type message: a string or list of strings 
    :param data: arbitrary sequence of bytes
    :param id: integer relevant to the event source
    :param category: integer relevant to the event source
    :param principal: who the event was logged by
    :type principal: anything accepted by :func:`accounts.principal`
    

Classes
-------

_EventLogEntry
~~~~~~~~~~~~~~

..  class:: _EventLogEntry (event_log_name : string, event_log_entry)

    An internal class corresponding to one record in an event log.
    It exposes the attributes of the record in a Pythonic manner,
    converting values to their WinSys equivalent where relevant.
    Consistent with the rest of the WinSys package, the names
    have been converted from their TitleCase originals to a
    lower_with_underscore version.
    
    .. attribute:: record_number
    
    The unique identifier of this record within this event log. May
    not correspond to the record's position in the current log since
    records can be cleared or purged.
    
    .. attribute:: time_generated
    
    Python datetime value corresponding to the record's timestamp
    
    .. attribute:: event_id
    
    Id of the event with relevance to the corresponding event source
    
    .. attribute:: event_type
    
    One of the :data:`EVENTLOG_TYPE` values
    
    .. attribute:: event_category
    
    Category of the event with relevance to the corresponding event source
    
    .. attribute:: sid
    
    :class:`accounts.Principal` Principal which logged the record
    
    .. attribute:: computer_name
    
    Name of the computer on which the record was logged
    
    .. attribute:: source_name
    
    Name of the event source which the record was logged against
    
    .. attribute:: data
    
    Arbitrary data associated with the log record
    
    .. attribute:: message
    
    The message associated with the record. This has already been formatted
    and the corresponding strings filled in.


EventLog
~~~~~~~~

..  class:: EventLog (computer : string, name : string)

    Typically instantiated via the :func:`event_log` function, which uses
    the friendlier moniker of name. The ``EventLog`` class does its
    best to treat the corresponding event log as a Python sequence, allowing
    forward and reverse iteration and item access. (The latter will not be
    fast as it essentially iterates over the log until the right item is
    found.)
    
    The records in the log are represented by instances of the internal
    :class:`_EventLogEntry` class which exposes the attributes of the
    log record in a Pythonic manner.
    
    .. attribute:: file
    
    The real file which holds the database for this event log
    
    .. attribute:: retention

    How many seconds the records should be kept for before purging
    
    .. method:: __len__
    
    Queries the underlying implementation for the current number of records
    in the corresponding event log. NB This may not be the same as the maximum
    record number since event logs can be purged and cleared. To determine
    efficiently the number of records currently in the log::
    
      from winsys import event_logs
      print len (event_logs.event_log ("Application"))
    
    .. method:: __iter__
    
    Implement the iterator protocol so that the event log itself can be treated
    as an iterable. To iterate over the records in the log, oldest first::
    
      from winsys import event_logs
      for record in event_logs.event_log ("Application"):
        print record
    
    cf :meth:`__reversed__` for iterating in reverse order.
    
    .. method:: __reversed__
    
    Implement the reverse iterator protocol so the event log can be iterated
    over in reverse, ie latest first::
    
      from winsys import event_logs
      for record in reversed (event_logs.event_log ("Application")):
        print record
        
    .. method:: __getitem__
    
    Allow random access to this event log by record position. NB This
    simply iterates over the event log in the right order until it
    finds the right record so it won't be fast. It's expected to be
    used to find the first or last records::
    
      from winsys import event_logs
      app = event_logs.event_log ("Application")
      
      print "First record:", app[0]
      print "Last record:", app[-1]
      
    At present, slices are not supported.
    
    .. method:: clear ([save_to_filename : string = None])
    
    Clear the event log, optionally saving the raw data first if a filename
    is specified. The save_to_filename is converted to unicode first, so it
    is possible to pass a :class:`fs.File` object.
    
    .. method:: log_event (source, *args, **kwargs)
    
    Convenience function which passes its parameters to the module-level
    :func:`log_event` function.


EventSource
~~~~~~~~~~~

..  class:: EventSource (computer : string, log_name : string, source_name : string)

    Generally instantiated from the module-level :func:`event_source` function
    which takes slightly friendlier arguments. The event source is a sideways
    concept in Windows event logs, providing the message structures for the
    events in a log. Most user event sources register against the Application log
    and this is treated as the default where relevant.
    
    Most of the functionality here is expected to be used internally to the
    module, but the :meth:`create` and :meth:`delete` methods are user-oriented.
    The class is its own context manager, but again this is principally to
    support the module-level :func:`log_event` function.
    
    .. attribute:: event_message_file
    
    The DLL containing the messages which the event source supports. For simple
    Python event sources this will be the win32evtlog.pyd file.
    
    .. attribute:: types_supported
    
    List of :data:`EVENTLOG_TYPE` name strings supported by this event source.
    
    .. classmethod:: create (name[, event_log_name=DEFAULT_LOG_NAME])
    
    Register a new event source in the registry, using the default pywin32-supplied
    DLL and event types. By default the source will be registered against the
    Application event log.
    
    .. method:: delete
    
    Remove this event source from the registry
    
    .. method:: log_event (*args, **kwargs)
    
    Convenience function which passes its parameters to the module-level
    :func:`log_event` function.


References
----------

..  seealso::

    `Event Logs <http://msdn.microsoft.com/en-us/library/FIXME.aspx>`_
      Documentation on microsoft.com for event logs
     
    :doc:`cookbook/event_logs`
      Cookbook examples of using the eventlogs module

To Do
-----

* New Vista / 2008 Event Logs mechanism
* Some way of incorporating DLLs of messages
