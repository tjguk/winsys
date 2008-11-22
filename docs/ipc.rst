:mod:`ipc` -- Interprocess Communication
========================================

..  module:: ipc
    :synopsis: Pythonic access to Windows IPC mechanisms
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>

Introduction
------------

The IPC module offers an interface to the various forms of interprocess
communication available under windows: mailslots, events, named pipes,
mutexes, sempahores and waitable timers. At least, that's the plan.
At the time of writing, only mailslots and events are in there. But
the rest are definitely on the way.

Exceptions
----------

..  exception:: x_ipc

    Base of all exceptions in this module; subclass of :exc:`core.x_winsys`
    
Functions
---------

..  function:: mailslot (mailslot[, message_size=0, timeout_ms=-1]) -> Mailslot object
    
    Factory function to return a :class:`Mailslot` object with the given
    name, number of messages and timeout in milliseconds. If ``name``
    is not an absolute mailslot name (looking like :file:`\\\\...\\mailslot\\...`)
    it is assumed to be a local mailslot and is prefixed with
    :file:`\\\\.\\mailslot\\`. If ``name`` is None, None is returned and the other
    parameters are ignored. If ``name`` is a ``Mailslot`` instance, it is returned
    unaltered and the remaining parameters are ignored.

..  function:: event (event[, initially_set=0, needs_manual_reset=0, security=None]) -> Event object
    
    Factory function to return a :class:`Event` object with the given
    name and flags. If ``event`` is None, None is returned and the remaining
    parameters are ignored. If ``event`` is an ``Event`` instance, it is returned
    unaltered and the remaining parameters are ignored.
    
    
Classes
-------

..  toctree::

    mailslots
    events
    
References
----------

..  seealso::

    `Synchronisation <http://msdn.microsoft.com/en-us/library/ms686353(VS.85).aspx>`_
     Documentation on microsoft.com for synchronisation objects

To Do
-----

* Named Pipes
* Waitable Timers
* Mutexes
* Waits