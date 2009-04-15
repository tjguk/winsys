:mod:`registry` -- Registry
===========================

..  automodule:: registry
    :synopsis: Pythonic access to the registry
    :show-inheritance:
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>


Constants
---------

..  data:: REGISTRY_HIVE
    
    Registry roots (:const:`HKEY_CURRENT_USER`, :const:`HKLM`, etc.)
    
..  data:: REGISTRY_ACCESS
    
    Access rights to registry keys (:const:`KEY_ALL_ACCESS`, :const:`KEY_QUERY_VALUE`, etc.)
    
..  data:: REGISTRY_VALUE_TYPE

    Types of registry values (:const:`REG_SZ`, :const:`REG_DWORD`, etc.)


Exceptions
----------

..  autoexception:: x_registry
..  autoexception:: x_moniker
..  autoexception:: x_moniker_ill_formed
..  autoexception:: x_moniker_no_root    

Functions
----------

..  autofunction:: create_moniker
..  autofunction:: registry
..  autofunction:: values
..  autofunction:: keys
..  autofunction:: copy
..  autofunction:: delete
..  autofunction:: create
..  autofunction:: walk
..  autofunction:: flat
..  autofunction:: parent

Classes
-------

..  autoclass:: Registry
    :members:


References
----------

..  seealso::

    :doc:`cookbook/registry`
      Cookbook examples of using the registry module

To Do
-----

* New Vista / 2008 Registry funcs (transactions etc.)
* Export-a-like functionality to create a human-readable export function