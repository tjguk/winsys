:mod:`registry` -- Registry
===========================

..  automodule:: registry
    :synopsis: Pythonic access to the registry
    :show-inheritance:
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>


Constants
---------
..  autodata:: REGISTRY_HIVE
..  autodata:: REGISTRY_ACCESS
..  autodata:: REGISTRY_VALUE_TYPE

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
    
    ..  automethod:: __add__

References
----------
..  seealso::

    :doc:`cookbook/registry`
      Cookbook examples of using the registry module

To Do
-----
* New Vista / 2008 Registry funcs (transactions etc.)
* Export-a-like functionality to create a human-readable export function