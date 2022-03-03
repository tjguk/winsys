.. currentmodule:: constants
.. highlight:: python
   :linenothreshold: 1

Using the constants module
==========================

Create constants set for file attributes
----------------------------------------
File attributes are represented by a bitmask set of constants,
all starting with FILE_ATTRIBUTES. Many of these are defined
in the win32file module. Some were added more recently and
have be added specifically.

..  literalinclude:: constants/file_attributes.py

Discussion
~~~~~~~~~~
The most common way of initialising a :class:`Constants` structure
is by pulling in all constants following a naming pattern from one
of the pywin32 modules. In this case, this leaves some useful
constants undefined so we add them in by creating a dictionary
with their values, and then passing that to the original object's
:meth:`Constants.update` function which accepts any dictionary-like
object.

Like all winsys objects, the constants objects have a :meth:`core._WinSysObject.dump`
method which provides a readable display of its values.

Show file access flags
----------------------
File access is a wide bitmask of flags in each ACE in the filesystem DACL.
It represents a set of access flags, named in the :const:`fs.FILE_ACCESS`
constants. Look at each ACE in turn and indicate the trustee and the
set of operations permtted.

..  literalinclude:: constants/file_access_flags.py

Discussion
~~~~~~~~~~
The :meth:`Constants.names_from_value` method returns the list of
constant names corresponding to the single value by comparing their
bitmasks. No check is made to see whether any bits are left "unclaimed"
nor whether any flags overlap partly or wholly (ie are synonyms).