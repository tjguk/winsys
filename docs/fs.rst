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
..  autofunction:: entry
..  autofunction:: file
..  autofunction:: dir
..  autofunction:: get_parts

Classes
-------

.. toctree::
   :maxdepth: 1
   
   fs_filepath
   fs_entry
   fs_file
   fs_dir

Constants
---------
..  autodata:: FILE_ACCESS
..  autodata:: FILE_SHARE
..  autodata:: FILE_NOTIFY_CHANGE
..  autodata:: FILE_ACTION
..  autodata:: FILE_ATTRIBUTE
..  autodata:: PROGRESS
..  autodata:: MOVEFILE
..  autodata:: FILE_FLAG
..  autodata:: FILE_CREATION
..  autodata:: VOLUME_FLAG
..  autodata:: DRIVE_TYPE
..  autodata:: COMPRESSION_FORMAT
..  autodata:: FSCTL

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
