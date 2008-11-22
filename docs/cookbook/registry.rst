Examples of using the registry module
=====================================

.. highlight:: python
   :linenothreshold: 1

.. _copy-one-registry-key-to-another:

Copy one registry key to another
--------------------------------

**Description**: Copy an existing registry key to a new one and
set the new key's security so that only the current user has
change rights and all other users have read-only. Finally, display
the details of the new top-level key, including its security.

..  literalinclude:: registry_copy_key.py

**Discussion**: Blha Blah