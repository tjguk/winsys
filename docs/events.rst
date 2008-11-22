Events
======

..  currentmodule:: ipc

..  class:: Event ([security=None, needs_manual_reset=0, initially_set=0, name=None])

    An event object is an interprocess (but not intermachine) synchronisation
    mechanism which allows one or more threads of control to wait on others.
    The most common configuration is given by the defaults: anonymous, 
    not set initially, and automatically reset once set (ie only set for long 
    enough to release any waiting threads and then reset. A common
    variant is a named event which can then be referred to easily by other
    processes without having to pass handles around. This is why the :func:`ipc.event`
    function reverses the order of parameters and takes the name first.
    
    The Event class mimics Python's Event objects which are in any case very
    close to the semantics of the underlying Windows object. For that reason,
    although :meth:`clear` is used to reset the event, :meth:`reset` is also
    provided as an alias, matching the Windows API.
    
    ..  method:: pulse
    
        Briefly set the event and then reset it
        
    ..  method:: set
    
        Set the event, causing waiting threads to release.
        
    ..  method:: clear
    
        Reset the event.
        
    ..  method:: reset
    
        Alias for :meth:`clear`
        
    ..  method:: wait ([timeout_s=-1])
    
        Block for at most timeout_s seconds until the event is set. By default
        block forever. 
        *NB* The timeout value is in (possibly fractional) seconds, whereas the 
        underlying windows API expects timeouts in milliseconds.

    ..  method:: isSet
    
        return True if the event is set, False otherwise.
    
