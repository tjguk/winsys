# -*- coding: iso-8859-1 -*-
import win32api
import win32con
import win32process

import pywintypes
from winsys import constants, core, exc, utils

class x_processes (exc.x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_processes)

class Process (core._WinSysObject):

  def __init__ (self, command, inherit_handles=True, flags=0, environment=None, current_directory=None, startupinfo=None):
    core._WinSysObject.__init__ (self)
    process_info = wrapped (
      win32process.CreateProcess,
      None,
      command,
      None,
      None,
      inherit_handles,
      flags,
      environment,
      current_directory,
      startupinfo
    )
    self.hProcess, self.hThread, self.pid, self.tid = process_info

  @classmethod
  def from_handles (cls, hProcess, hThread, pid, tid):
    self.hProcess, self.hThread, self.pid, self.tid = hProcess, hThread, pid, tid

def process (process=None, flags=0, startupinfo=None):
  if process is None:
    return Process.from_handles (
      wrapped (win32api.GetCurrentProcess),
      wrapped (win32api.GetCurrentThread),
      wrapped (win32api.GetCurrentProcessId),
      wrapped (win32api.GetCurrentThreadId)
    )
  elif isinstance (process, Process):
    return process
  else:
    s = win32process.STARTUPINFO ()
    if isinstance (startupinfo, type (s)):
      s = startupinfo
    elif startupinfo:
      for k, v in startupdict.items ():
        setattr (s, k, v)
    return Process (command, flags=flags, startupinfo=s)
