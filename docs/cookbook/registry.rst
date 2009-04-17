.. currentmodule:: registry
.. highlight:: python
   :linenothreshold: 1

Using the registry module
=========================

The examples here all refer to the :mod:`registry` module.

.. _copy-one-registry-key-to-another:

Copy one registry key to another
--------------------------------
Copy an existing registry key to a new one and
set the new key's security so that only the current user has
change rights and all other users have read-only. Finally, display
the details of the new top-level key, including its security.

..  literalinclude:: registry/copy_key.py

Discussion
~~~~~~~~~~
The functions in the :mod:`registry` module hand off any references
to a registry key to the :func:`registry` function which is
as accepting as possible. Here, we're referring to the local machine
(there's no server-style \\\\ prefix in either moniker) and using
the HKLM/HKCU shortcut styles. In fact the code would work equally
well if a remote machine were to specified on either side, assuming
that the necessary permissions were in place.

The :meth:`Registry.security` method acts as a context
manager, allowing a series of changes to the registry key's
security descriptor. Here we are breaking the inheritance which
the new key has inherited automatically, without copying the
existing permissions over first. Then we add a new DACL with
just two permissions: allowing the logged-on user full control;
and allowing all authenticated users read access. The 3-tuples
are passed to the :meth:`security.ace` function.

Finally, to demonstrate that the security has been applied, we
call the registry key's :meth:`Registry.dump` method
which produces useful information about the key and its security
in a readable format.

Find a string in the registry
-----------------------------
Search the registry under a particular root and find a value which
contains the searched-for string. Output the registry key, the value
name and the value itself.

..  literalinclude:: registry/find_value.py

Discussion
~~~~~~~~~~
We use :func:`dialogs.dialog` to select the root key and
the string to search for. We then walk the registry from that
key downwards, skipping over any keys or values to which we
do not have access. When we find a value which matches our
search term, we output the key name, value label and the value
which matched.