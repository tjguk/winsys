Using the event_logs module
===========================

Log an event against an event source
------------------------------------

Description
~~~~~~~~~~~
Log an information event against a WinSys event source,
creating it if does not already exist. Once the event is written, remove
the event source.

..  literalinclude:: log_event.py
    :language: python
    :linenos:

Discussion
~~~~~~~~~~
Events are always logged against a specific event source. We can create
a simple event source which will render single-string messages. For the purposes of
demonstration, we attempt to pick up the event source if it already exists and to
create it if it does not. We use the class-level convenience function to log the
event against the source, which simply hands off to the module-level function of
the same name.

An event source can be deleted at any time: its records simply become "orphans"
in that the system will no longer be able to format their messages since it
won't know the location of the DLL which contains the corresponding strings.


List the 10 most recent records in each event log
-------------------------------------------------

Description
~~~~~~~~~~~
Go through each event log on the system and list the 10 most recent
events.

..  literalinclude:: latest_10_events.py
    :language: python
    :linenos:
    
Discussion
~~~~~~~~~~
By default, iterating over an event log starts oldest first. To pick up
the most recent records, we reverse the iterator. This makes use of the
:meth:`event_logs.EventLog.__reversed__` magic method which starts a reverse iterator. Without that,
the implementation would fall back to a __getitem__-based sequence
solution, asking for [-1] and then [-2] and so on. Since our :meth:`event_logs.EventLog.__getitem__`
implementation actually iterates anyway, this would be a less-than-optimal
solution.

The standard __str__ for an event log record shows the record number,
the source and the event type. We add here the record's timestamp.


Write to CSV selected events from a remote event log
----------------------------------------------------

Description
~~~~~~~~~~~
Go through the a remote System event log and write to CSV the
record number, id and message for records matching a particular
event source and type.

..  literalinclude:: remote_events.py
    :language: python
    :linenos:

Discussion
~~~~~~~~~~
We use the winsys :mod:`dialogs.dialog` module convenience function to request
the name of the remote computer and the source and event type from the user.
It would be possible to pick out the list of event sources for a computer
(using the :func:`event_logs.event_sources` function), but there's no mechanism
within the dialogs module for updating one field on the basis of another, so
we could only pre-populate with the valid list for one particular computer.

The module-level convenience function :func:`event_logs.event_log` returns an
instance of an :class:`event_logs.EventLog` matching the computer and event log name in the
UNC-style moniker. The standard iterator goes from the oldest first forwards.
If we wanted to see the records in reverse chronological order, we'd use the
reversed builtin to invoke the class's :meth:`event_logs.EventLog.__reversed__`
method.