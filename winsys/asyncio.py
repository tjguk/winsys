# -*- coding: iso-8859-1 -*-
ur"""AsyncIO objects wrap the Win32 Overlapped API. They are instantiated by
passing a handle which has been opened for Overlapped IO. They can be waited
on by the functions in the :mod:`ipc` module and are True when complete,
False otherwise.
"""
import pywintypes
import winerror
import win32event
import win32file

from winsys import constants, core, exc, ipc, utils

class x_asyncio (exc.x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_asyncio)

class AsyncIO (core._WinSysObject):

  def __init__ (self):
    core._WinSysObject.__init__ (self)
    self.event = ipc.event (needs_manual_reset=True)
    self.overlapped = wrapped (win32file.OVERLAPPED)
    self.overlapped.hEvent = self.event.pyobject ()

  def pyobject (self):
    ur"""Return the pyobject of the underlying event so that this object can
    be waited on by the :func:`ipc.all` or :func:`ipc.any` functions
    """
    return self.event.pyobject ()

  def is_complete (self):
    ur":returns: `True` if the IO has completed"
    return self.event.isSet ()
  __nonzero__ = is_complete

  def wait (self):
    ur"""Wait for the IO to complete in such a way that the wait can
    be interrupted by a KeyboardInterrupt.
    """
    while not self.event.wait (timeout_s=0.5):
      pass

class AsyncHandler (AsyncIO):

  BUFFER_SIZE = 4096

  def __init__ (self, handle, buffer_size=BUFFER_SIZE):
    AsyncIO.__init__ (self)
    self.handle = handle

class AsyncWriter (AsyncHandler):

  def __init__ (self, handle, data):
    AsyncHandler.__init__ (self, handle)
    self.data = data
    wrapped (win32file.WriteFile, self.handle, data, self.overlapped)

class AsyncReader (AsyncHandler):

  BUFFER_SIZE = 4096

  def __init__ (self, handle):
    AsyncHandler.__init__ (self, handle)
    self.buffer = win32file.AllocateReadBuffer (self.BUFFER_SIZE)
    wrapped (win32file.ReadFile, self.handle, self.buffer, self.overlapped)

  def data (self):
    ur"""Wait until the IO has completed and return the data from the read. This
    is expected to be called after is_complete is true.
    """
    n_bytes = win32file.GetOverlappedResult (self.handle, self.overlapped, True)
    return str (self.buffer)[:n_bytes]
