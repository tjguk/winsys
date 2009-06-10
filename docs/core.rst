:mod:`core` -- Core objects
===========================

..  module:: core
    :synopsis: Core objects for the WinSys package
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>

Introduction
------------

The :mod:`core` module is not intended to be used by
user code but establishes base objects for all other
WinSys modules.


Exceptions
----------

..  exception:: x_winsys

    Base of all exceptions in the package
    
..  exception:: x_access_denied

    Common exception corresponding to an access denied error
    
..  exception:: x_not_found

    Common exception corresponding to a file or path not found error
    
..  exception:: x_invalid_handle

    Common exception corresponding to a handle not found error
    

Classes
-------

..  class:: _WinSysObject

    Not intended to be used by instantiated by itself, this class forms the
    basis for most of the classes in the WinSys package. It provides useful
    defaults for common functionality, including filling in comparison
    functions (:meth:`__ne__`, :meth:`__le__` and so on) so that total
    ordering can be assumed for all derived classes.
    
    ..  method:: as_string
    
        By default, the name of the class; usually overriden in derived
        classes to be some meaningful name. Forms the basis for the
        :meth:`__str__` and :meth:`__unicode__` methods.
        
    ..  method:: dumped
    
        By default, simply dump the result of :meth:`as_string` to give a
        usable if unhelpful default. Intended to be overriden by subclasses,
        generally to stack attribute values into a list of strings which is
        then passed to :func:`utils.dumped` to fill in the curly brackets.

    ..  method:: dump
    
        Calls the underlying :meth:`dumped` implementation to provide a
        convenient representation of the object's data.

Logging Functions
-----------------

The :mod:`core` module establishes a simple logger under the name "winsys", 
logging to filename :file:`winsys.log`. The logger's *debug*, *log*, *info*,
*warn* and *error* methods are imported directly into the module's namespace.
