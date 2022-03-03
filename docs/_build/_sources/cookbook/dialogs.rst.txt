.. currentmodule:: dialogs
.. highlight:: python
   :linenothreshold: 1

Using the dialogs module
========================

The examples here all refer to the :mod:`dialogs` module.

Ask the user for input
----------------------
This is the simplest kind of dialog box: a one-line edit
control with [Ok] and [Cancel].

..  literalinclude:: dialogs/ask_for_input.py


Prompt for a filename to open
-----------------------------
Ask the user for a filename, check that the file exists,
and then use os.startfile to open the file. Allow the
user to type the filename in, drag-and-drop a file from
Explorer, or select from a dialog box.

..  literalinclude:: dialogs/ask_for_filename.py

Discussion
~~~~~~~~~~
All edit controls accept files drag/dropped from Explorer.
In addition, by specifying a third field for the "Filename"
input, we can call out to another dialog box to select the
file. Here we use the one supplied by winsys, but the only
requirement for the callback is that it return a string or
None to indicate no change.

A :class:`fs.Entry` object evaluates to True if the file
it represents exists on the file system.