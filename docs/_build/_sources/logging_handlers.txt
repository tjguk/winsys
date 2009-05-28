:mod:`logging_handlers` -- Additional Logging Handlers
======================================================

..  module:: logging_handlers
    :synopsis: Additional handlers for the builtin logging module
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>

Introduction
------------

Python's `builtin logging module <http://docs.python.org/library/logging.html>`_
offers the concept of `handlers <http://docs.python.org/library/logging.html#handlers>`_
each of which takes the logged message and passes to an output channel. There
are handlers provided for screen, files, NT Event Logs and so on. This module
offers two handlers to output to a named Windows mailslot. It makes use of the
:class:`ipc.Mailslot` class and can write to a one-time
mailslot or to a mailslot which is running permanently.

The sort of situation where this might be useful is where you have a number
of system routines running on and off. If they all log to the same mailslot,
say on an administrator's desktop, then he can see the progress of all in one
place. Better still, if they log to all the mailslots of the same name in the
domain, then everyone can have a logging screen running on their desktop which
they can start up and close down at will to see the current progress.

Classes
-------

..  class:: MailslotHandler (mailslot_name : string)

    Set up a handler going to the named mailslot. Note that the usual
    possibilities obtain for mailslot names: an unqualified name must exist
    on the local machine; a computer or domain-qualified name will broadcast
    to that machine or that domain without checking existence; a * will just
    broadcast, full-stop.
    
    The close function sends a None to the receiving mailslot, intended to act as a
    prompt to shut down. (Although that's obviously in the hands of the receiver).
    
..  class:: PermanentMailslotHandler (mailslot_name : string)

    Subclass the MailslotHandler and override the close function so that it
    doesn't send the shutdown token to the receiving mailslot(s).
    
