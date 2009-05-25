:mod:`fs` -- Files, Directories, &c.
====================================

..  module:: fs
    :synopsis: Files, Directories, &c.
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>


Introduction
------------
The fs module makes it easy to work with files, directories, drives, volumes and paths within the Windows filesystems.
The most common entry-point is to use :func:`entry` to return a :class:`File` or :class:`Dir` object, although you
can use :func:`file` or :func:`dir` directly. Instances of these classes need not exist on any filesystem -- in fact
they equate to True or False according to the existence or not of a corresponding filesystem object. But they can
be the source or target of all the usual filesystem operations. In common with other modules in this package, 
functionality is provided at the module level as well as at the class level, so you can, eg, call :meth:`File.copy` 
or :func:`copy` to copy a file to another location.

An important part of the module is the :class:`FilePath` class which eases manipulation of filesystem paths and is
at the same time a subclass of unicode, so is accepted in system calls where strings are expected.

Functions
----------

Factories
~~~~~~~~~
..  autofunction:: entry
..  autofunction:: file
..  autofunction:: dir
..  autofunction:: drive
..  autofunction:: volume

stdlib Extras
~~~~~~~~~~~~~
Several functions are either convenient or superior
replacements to equivalent stdlib functionality.

..  autofunction:: listdir
..  autofunction:: glob
..  autofunction:: mkdir
..  autofunction:: rmdir
..  autofunction:: walk
..  autofunction:: flat
..  autofunction:: move
..  autofunction:: copy
..  autofunction:: delete
..  autofunction:: exists
..  autofunction:: zip
..  autofunction:: touch

Helpers
~~~~~~~
..  autofunction:: get_parts
..  autofunction:: normalised
..  autofunction:: handle
..  autofunction:: relative_to
..  autofunction:: attributes

Additional Filesystem Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
..  autofunction:: mount
..  autofunction:: dismount
..  autofunction:: drives
..  autofunction:: volumes
..  autofunction:: mounts
..  autofunction:: watch

Classes
-------

.. autoclass:: _Attributes

.. toctree::
   :maxdepth: 1

   fs_drive_vol
   fs_filepath
   fs_entry
   fs_file
   fs_dir

Constants
---------

.. toctree::
   :maxdepth: 1
   
   fs_constants

Exceptions
----------
..  autoexception:: x_fs
..  autoexception:: x_no_such_file
..  autoexception:: x_too_many_files
..  autoexception:: x_invalid_name
..  autoexception:: x_no_certificate
..  autoexception:: x_not_ready

References
----------
..  seealso::

    :doc:`cookbook/fs`
      Cookbook examples of using the fs module
