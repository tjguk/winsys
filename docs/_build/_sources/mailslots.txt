Mailslots
=========

..  currentmodule:: ipc

..  exception:: x_mailslot_invalid_use

    Indicates that an attempt has been made to use a mailslot for reading *and* writing.
    
..  exception:: x_mailslot_empty

    Raised when a call to :meth:`Mailslot.get` times out with nothing in the mailslot.

..  class:: Mailslot (name : string[, message_size=0, timeout_ms=-1])

    A mailslot is a one-way channel of communication implemented over UDP
    which allows messages to be sent to a named mailslot on one or more
    computers in the network regardless of the existence of a listening
    mailslot. This is ideally suited for, eg, logging to one or more
    remote computers. cf :class:`MailslotHandler` and :mod:`mailslot_listener`
    for an implementation of this.
    
    The Mailslot class mimics Python's Queue object although the semantics
    are necessarily a little different. In particular, a Mailslot can only
    be read from or written to within one process: not both. The same class
    is used for readers and writers; the first use (a put or a get) freezes
    the object's use and from that point on only that same use is allowed.
    A :exc:`x_ipc_invalid_use` is raised if any other use is attempted.
    
    Although this class can be instantiated directly, it is expected that
    the :func:`mailslot` function will be used, which can offer a slight
    ease of use in common naming situations.
    
    A Mailslot is its own iterator and its own context manager so a common 
    usage for a reading mailslot might be::
    
      from winsys import ipc
      
      with ipc.mailslot ("LISTENER") as listener:
        for message in listener:
          print message
          
    while a writing mailslot could do the following to broadcast a message
    to all mailslots named LISTENER anywhere in the network::
    
      from winsys import ipc
      
      with ipc.mailslot (r"\\*\mailslot\LISTENER") as writer:
        writer.put ("HELLO")
    
    For a discussion of mailslot naming and usage, see: http://msdn.microsoft.com/en-us/library/aa365576(VS.85).aspx.
    
    ..  method:: qsize
    
        Return the number of items waiting in the mailslot to be read.
        **NB This will freeze the mailslot as a reader**
        
    ..  method:: empty
    
        Return True if there is nothing in the mailslot to be read, False otherwise.
        **NB This will freeze the mailslot as a reader**
        
    ..  method:: full
    
        Return True if the number of messages in the mailslot is the maximum
        allowed.
        **NB This will freeze the mailslot as a reader**
        
    ..  method:: get ([block=True, timeout_ms=-1])
    
        Pop the oldest waiting message from the mailslot, waiting for one to
        arrive if block is True, waiting no longer than timeout_ms.
        **NB This will freeze the mailslot as a reader**

    ..  method:: get_nowait
    
        Shortcut for :meth:`get (False, 0)`
        **NB This will freeze the mailslot as a reader**

    ..  method:: put (data)
    
        Send data to this mailslot (which may, depending on its name, map
        to all mailslots of that name in a domain or available on the network).
        **NB This will freeze the mailslot as a writer**

    ..  method:: close
    
        Close the mailbox handle, making it impossible to write/read from
        this mailbox. This method is called automatically if :class:`Mailslot`
        is used as a context manager.