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


Functions
----------

Factories
~~~~~~~~~

..  autofunction:: mailslot
..  autofunction:: event

Helpers
~~~~~~~

..  autofunction:: any
..  autofunction:: all


Classes
-------

..  toctree::

    mailslots
    events

Constants
---------

..  autodata:: WAIT

Exceptions
----------

..  autoexception:: x_ipc
..  autoexception:: x_mailslot
..  autoexception:: x_mailslot_invalid_use
..  autoexception:: x_mailslot_empty
..  autoexception:: x_mailslot_message_too_big
..  autoexception:: x_mailslot_message_too_complex


References
----------

..  seealso::

    `Synchronisation <http://msdn.microsoft.com/en-us/library/ms686353(VS.85).aspx>`_
     Documentation on microsoft.com for synchronisation objects

    :doc:`cookbook/ipc`
      Cookbook examples of using the ipc module

To Do
-----

* Named Pipes
* Waitable Timers
* Mutexes
* Waits