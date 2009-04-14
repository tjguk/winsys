:mod:`registry` -- Registry
===========================

..  automodule:: winsys.registry
    :synopsis: Pythonic access to the registry
    :show-inheritance:
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>


Constants
---------

..  data:: REGISTRY_HIVE
    
    All possible registry roots
    
..  data:: REGISTRY_ACCESS
    
    Valid access rights to registry keys
    
..  data:: REGISTRY_VALUE_TYPE

    Possible types for registry values


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

Registry
~~~~~~~~

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