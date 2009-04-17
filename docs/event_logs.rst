:mod:`event_logs` -- Event Logs
===============================

..  module:: event_logs
    :synopsis: Read and write event log entries
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


Functions
----------

Of these functions, the two you're most likely to need are: :func:`event_log`,
which returns an :class:`EventLog` corresponding to the named log,
which you can then iterate over; and :func:`log_event`, which logs an event
against a named source.

..  autofunction:: event_logs
..  autofunction:: event_log
..  autofunction:: event_sources
..  autofunction:: event_source
..  autofunction:: log_event 

Classes
-------

..  autoclass:: _EventLogEntry
    :members:
    
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


..  autoclass:: EventLog
    :members:

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
      
      print "Oldest record:", app[0]
      print "Latest record:", app[-1]
      
    At present, slices are not supported.
    

..  autoclass:: EventSource
    :members:

    .. attribute:: event_message_file
    
    The DLL containing the messages which the event source supports. For simple
    Python event sources this will be the win32evtlog.pyd file.
    
    .. attribute:: types_supported
    
    List of :data:`EVENTLOG_TYPE` name strings supported by this event source.

Exceptions
----------

..  autoexception:: x_event_logs

Constants
---------

..  autodata:: EVENTLOG_READ
..  autodata:: EVENTLOG_TYPE


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
* Using EVENTLOG_SEEK_READ for better random access