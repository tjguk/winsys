.. currentmodule:: ipc
.. highlight:: python
   :linenothreshold: 1

Using the ipc module
====================

Writing to a network logger
---------------------------
Sending log entries to a logging mailslot which may or may not be running
without needing to know which server is hosting it.

..  literalinclude:: ipc/network_mailslot.py

This is where mailslots really score over named pipes, sockets, etc. You can
send messages to a named mailslot without knowing where it is or if it's even
running. Furthermore, there may be several active mailslots with the same
name, all of which will receive the data sent.

The obvious application is for centralised or distributed logging but it
could also be used as a form of pub-sub mechanism, at least for small
pieces of data. The maximum message size across the network is about 400 bytes.

The :func:`mailslot` function is the quickest way to get hold of a mailslot
for reading or writing. It provides useful defaults especially for local
mailslots where the full path can be determined. Since the underlying
:class:`Mailslot` can be context-managed, I've enclosed the activity of
each mailslot in a "with" block.

For simplicity I've run a reading mailslot inside a thread. For a clearer
demonstration you could run the same code in a separate process, ideally on
a separate machine within the same domain.

Read and write a local mailslot
-------------------------------
Read and write to local named mailslot, interleaving reads and writes.

..  literalinclude:: ipc/local_mailslot.py

Although the most likely application of mailslots is from separate threads or processes
on separate machines even, it's quite possible for the same thread to read from
and write to the same mailslot. The caveat is that one object must be obtained
for reading and another for writing. They are linked by passing the same name to
:func:`mailslot`.

We make use of the fact that the :class:`Mailslot` objects are mimicking Python's
`Queue` objects. This includes a :meth:`Mailslot.get` method which has a timeout
option. Using this, we can check for active messages and pass on by if none is
present. We then randomly put one word from our message into the mailslot from
the writer's end and go round again. Finally, we send our STOP sentinel so that
both ends release their respective mailslot handles.


Mailslot as an iterable
-----------------------
Iterate over the contents of a mailslot

..  literalinclude:: ipc/iterable_mailslot.pyt