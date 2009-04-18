.. currentmodule:: fs
.. highlight:: python
   :linenothreshold: 1

Using the fs module
===================

Take ownership of a file
------------------------
Take ownership of a file to which you have no other access.

..  literalinclude:: fs/take_ownership.py

The :meth:`take_ownership` method assumes that you have no existing
access to the object, so does not attempt to read its security at all
since this would probably fail. If you do not even have permission
to set the owner entry in the security descriptor you need to enable
the SeTakeOwnership privilege in your token. Best practice is to 
enable privileges for only as long as you need them, so the security
module's changed_privileges is a context manager which reverses the
privilege changes once it exits.


Find the sizes of top-level directories
---------------------------------------
For a given root directory, find the total size taken by all the
files in each of its top-level subdirectories, and display them
in descending order of size.

..  literalinclude:: fs/find_dir_sizes.py

The :func:`dialogs.dialog` function sets up a simple dialog box
requesting the name of the root directory (offering a push-button
for a standard selection dialog). Then the :meth:`Dir.dirs` method
iterates over all subdirectories of its directory, and :meth:`Dir.flat`
iterates over all the files underneath a directory from which we can
fetch their (compressed) size and sum them all up.

The rest is mostly standard Python gimmickry with sorting dictionaries
etc. The :func:`utils.size_as_mb` function provides a more human-readable
version of a number of bytes.