:mod:`iasyncio` -- Overlapped IO
================================

..  module:: asyncio
    :synopsis: Pythonic access to Overlapped API
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>

Introduction
------------

The :class:`AsyncIO` objects wrap Overlapped IO -- Microsoft's answer to
asynchronous IO -- to allow fairly easy access.


Classes
-------

..  autoclass:: AsyncIO
    :members:
    :undoc-members:
    :show-inheritance:

..  autoclass:: AsyncWriter
    :members:
    :undoc-members:
    :show-inheritance:

..  autoclass:: AsyncReader
    :members:
    :undoc-members:
    :show-inheritance:

Exceptions
----------

..  autoexception:: x_asyncio


References
----------

..  seealso::

    `Synchronisation <http://msdn.microsoft.com/en-us/library/ms686353(VS.85).aspx>`_
     Documentation on microsoft.com for synchronisation objects

    :doc:`cookbook/asyncio`
      Cookbook examples of using the asyncio module
