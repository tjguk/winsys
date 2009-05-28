.. currentmodule:: accounts
.. highlight:: python
   :linenothreshold: 1

Using the accounts module
=========================

The examples here all refer to the :mod:`accounts` module.

Get the logged-on user's account
--------------------------------
Get the account for the logged-on user.

.. literalinclude:: accounts/get_logged_on_user.py
   
Discussion
~~~~~~~~~~
This is so common a need that there is a module-level convenience function for the very purpose.


Act as another user
-------------------
Temporarily switch the current process to use another user's identity. Create
a file as that other user and then check that the file was created with that
owner. (Assumes the existence of a "python" user).

.. literalinclude:: accounts/act_as_another_user.py

Discussion
~~~~~~~~~~
There can be a lot of subtlety involved in switching users. The winsys
code at present takes a very straightforward approach which should work
for several cases. 

Since we're using the :class:`Principal` class itself as a context manager,
no password can be passed in, so the program automatically pops up a
standard Windows password UI with the username filled in. To pass a
password in automatically, use the :meth:`Principal.impersonate` method
which accepts a password and a logon type.

..  note::
    This hasn't been tested at all on Vista or W7 where
    the security model is much tighter, particularly with respect to raising
    privs.


Create a local user
-------------------
Create a new local user with minimum permissions and a password. 

..  literalinclude:: accounts/create_local_user.py

Discussion
~~~~~~~~~~
The new user will have no logon script, no home directory and will not be 
in the Users group. (This last means that it will not show up on the 
quick-logon screen in XP etc.). The same approach can be used for creating
a local group, except that the :meth:`Group.create` method should be called on
the :class:`Group` class instead.


Delete a local user
-------------------
Delete an existing local user

..  literalinclude:: accounts/delete_local_user.py

Discussion
~~~~~~~~~~
The same approach can be used for deleting a local group.