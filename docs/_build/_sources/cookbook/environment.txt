.. currentmodule:: environment
.. highlight:: python
   :linenothreshold: 1

Using the environment module
============================

The examples here all refer to the :mod:`environment` module.

Dump the current process environment
------------------------------------

..  literalinclude:: environment/dump_environment.py


Remove all Python installations from the PATH
---------------------------------------------

Prior, say, to installing a new version Python, make sure
that no existing Python installations remain on the PATH.
PATH is made up of the system PATH env var plus the user
PATH.

..  literalinclude:: environment/remove_python_from_path.py

The Python installations are listed in the registry under the
Software\Python key in HKLM and HKCU. That key has one subkey for
each version installed and the subkey holds its installation
directory in the default value of the InstallPath key.

We collect the unique list of installation directories and
filter the user and system PATH env vars in turn by including
only those paths which are not part of a Python installation.

We have to allow for case differences between the PATH and the
installation directories, and for the fact that some of the
install dirs have a trailing backslash while some don't.

..  note::
    For the purposes of not endangering your PATH, the critical
    line which actually updates the PATH is commented out and
    the would-be result is shown instead.