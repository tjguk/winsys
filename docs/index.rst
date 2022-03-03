WinSys - Python tools for the Windows Administrator
===================================================

*We read the Windows docs so you don't have to*

Introduction
------------

WinSys is a Python package which wraps aspects of the Windows API to make
them more Pythonic and usable by Windows administrators directly
from the interpreter or as part of a wider set of applications.
It targets recent versions of Python and reasonably recent versions of Windows.

It is unashamedly platform-specific: no hint of a concession towards more
Unix-like operating systems.  You can read about the design
philosophy and decisions in :ref:`about-winsys`. If you want to see some
examples, have a look in the :ref:`cookbook`.

WinSys is developed as an Open Source project and the project home,
together with issues list and browseable source code is at:

  https://github.com/tjguk/winsys

If you're interested in helping with the project let me know and I'll
add you to the project members list.

Example
-------

Copy a registry key from HKLM to HKCU and set its permissions so that
only the current user has change access while everyone else gets read.
Then dump the details of the new top-level key, including its security.

..  literalinclude:: cookbook/registry/copy_key.py
    :language: python
    :linenos:

This example makes use of the :mod:`registry`, :mod:`accounts` and :mod:`security` modules.
You can see :ref:`discussion <copy-one-registry-key-to-another>` of this example and more in the :ref:`cookbook`.

Download
--------

* pip::

    pip install winsys

* Git master::

    git clone git://github.com/tjguk/winsys.git

  and then, from within that clone::

    pip install -e .[all]

Copyright & License
-------------------

winsys is Copyright Tim Golden 2011 and is licensed under the
(GPL-compatible) MIT License: http://www.opensource.org/licenses/mit-license.php
