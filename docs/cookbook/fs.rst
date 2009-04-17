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
