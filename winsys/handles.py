# -*- coding: iso-8859-1 -*-
import win32api
import win32con
import win32file

import pywintypes
from winsys import constants, core, exc, utils

class x_handles (exc.x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_handles)

class Handle (core._WinSysObject):

  def __init__ (self, handle):
    core._WinSysObject.__init__ (self)
    self._handle = handle
    self.name = str (int (self._handle))

  def __int__ (self):
    return int (self._handle)

  def pyobject (self):
    return self._handle

  def duplicate (self, process=None, inheritable=True):
    target_process = processes.process (process).hProcess
    this_process = wrapped (win32api.GetCurrentProcess)
    return self.__class__ (
      wrapped (
        win32api.DuplicateHandle,
        this_process,
        self._handle,
        target_process,
        0,
        inheritable,
        win32con.DUPLICATE_SAME_ACCESS
      )
    )

  def read (self, buffer_size=0):
    data = ""
    while True:
      hr, _data = wrapped (win32file.ReadFile, self._handle, buffer_size)
      data += _data
      if hr == 0:
        break

  def write (self, data):
    wrapped (win32file.WriteFile, self._handle, data)

def handle (handle):
  if handle is None:
    return None
  elif isinstance (handle, int):
    return Handle (pywintypes.HANDLE (handle))
  else:
    return Handle (handle)
