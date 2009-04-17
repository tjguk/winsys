:mod:`fs` -- Files, Directories, &c.
====================================

..  automodule:: fs
    :synopsis: File, Directories, Volumes, Drives
    :show-inheritance:
..  moduleauthor:: Tim Golden <mail@timgolden.me.uk>


Functions
----------
..  autofunction:: entry
..  autofunction:: file
..  autofunction:: dir

Classes
-------
..  autoclass:: Entry
    :members:
    
..  autoclass:: File
    :members:
    
..  autoclass:: Dir
    :members:
    
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
