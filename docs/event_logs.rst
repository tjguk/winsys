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


Exceptions
----------

..  exception:: x_event_logs

    Base of all exceptions in this module; subclass of :exc:`core.x_winsys`

Functions
----------

..  PASS

Classes
-------

..  class:: EventLog (computer : string, name : string)

    Typically instantiated via the :func:`event_log` function, which uses
    the friendlier moniker of name. The ``EventLog`` class does its
    best to treat the corresponding event log as a Python sequence, allowing
    forward and reverse iteration and item access. (The latter will not be
    fast as it essentially iterates over the log until the right item is
    found.)

References
----------

..  seealso::

    `Event Logs <http://msdn.microsoft.com/en-us/library/FIXME.aspx>`_
     Documentation on microsoft.com for event logs

To Do
-----

* Write event logs entry
* New Vista / 2008 Event Logs mechanism
* Some way of incorporating DLLs of messages
