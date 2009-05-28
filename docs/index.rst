.. WinSys documentation master file, created by sphinx-quickstart on Fri Oct 31 15:35:06 2008.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

WinSys - Python tools for the Windows Administrator
===================================================

*We read MSDN so you don't have to*

Introduction
------------

WinSys is a Python package which wraps aspects of the Windows API to make
them more Pythonic and usable by Windows administrators directly
from the interpreter or as part of a wider set of applications.
It targets recent versions of Python and reasonably recent versions of Windows
although it's not yet up speed on Vista & x64.

It is unashamedly platform-specific: no hint of a concession towards more
Unix-like operating systems.  You can read about the design
philosophy and decisions in :ref:`about-winsys`. If you want to see some
examples, have a look in the :ref:`cookbook`. Or visit the :ref:`contents`
for an overview.

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

* easy_install:: 

    easy_install winsys

* MSI installers & Zipped archives:: 
  
    http://timgolden.me.uk/python/downloads/winsys/
    
  and then::
    
    winsys-x.y.z.msi
    
  or::
    
    unzip winsys-x.y.z.zip
    python setup.py install

* Subversion trunk::

    svn co http://winsys.googlecode.com/svn/trunk winsys

