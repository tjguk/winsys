# -*- coding: iso-8859-1 -*-
import re
import time

import pywintypes
import winerror
import win32event
import win32file

from winsys import constants, core, fs, security, utils
from winsys.exceptions import *

WAIT = constants.Constants.from_pattern (u"WAIT_*", namespace=win32event)
WAIT.update (dict (INFINITE=win32event.INFINITE))

PyHANDLE = pywintypes.HANDLEType

class x_ipc (x_winsys):
  pass
  
class x_mailslot (x_ipc):
  pass

class x_mailslot_invalid_use (x_ipc):
  pass

class x_mailslot_empty (x_ipc):
  pass
  
WINERROR_MAP = {
  winerror.ERROR_FILE_NOT_FOUND : x_not_found,
}
wrapped = wrapper (WINERROR_MAP, x_ipc)

class Mailslot (core._WinSysObject):
  
  def __init__ (self, name, message_size=0, timeout_ms=-1, *args, **kwargs):
    core._WinSysObject.__init__ (self, *args, **kwargs)
    self.name = name
    self.message_size = message_size
    self.timeout_ms = timeout_ms
    self._hRead = self._hWrite = None
    #
    # If the name is a local mailslot it could conceivably
    # be used for reading or for writing. If it is a
    # remote (including domain) mailslot, it can only
    # be written to.
    #
    if name.startswith (r"\\."):
      self._hWrite = None
    else:
      self._hWrite = self._write_handle ()

  def _read_handle (self):
    if self._hWrite is not None:
      raise x_mailslot_invalid_use ("Cannot read from this mailslot; it is used for writing")
    if self._hRead is None:
      self._hRead = wrapped (win32file.CreateMailslot, self.name, self.message_size, self.timeout_ms, None)
    return self._hRead
    
  def _write_handle (self):
    if self._hRead is not None:
      raise x_mailslot_invalid_use (u"Cannot write to this mailslot; it is used for reading")
    if self._hWrite is None:
      self._hWrite = wrapped (
        win32file.CreateFile,
        self.name, 
        fs.FILE_ACCESS.GENERIC_WRITE,
        fs.FILE_SHARE.READ, 
        None, 
        fs.FILE_CREATION.OPEN_EXISTING, 
        fs.FILE_ATTRIBUTE.NORMAL, 
        None
      )
    return self._hWrite
  
  def pyobject (self):
    if self._hRead:
      return self._hRead
    elif self._hWrite:
      return self._hWrite
    else:
      raise x_mailslot ("Mailslot has not yet been used for reading or writing")
  
  def __iter__ (self):
    while True:
      yield self.get ()
      
  def __enter__ (self):
    return self
    
  def __exit__ (self, *args):
    self.close ()
  
  def as_string (self):
    return self.name
    
  def dumped (self, level=0):
    output = []
    output.append ("name: %s" % self.name)
    output.append ("message_size: %s" % self.message_size)
    output.append ("timeout_ms: %s" % self.timeout_ms)
    if self._hRead:
      output.append ("in use for reading")
    elif self._hWrite:
      output.append ("in use for writing")
    else:
      output.append ("not yet used for reading or writing")
    return utils.dumped ("\n".join (output), level)
  
  def qsize (self):
    maxsize, nextsize, message_count, timeout = wrapped (win32file.GetMailslotInfo, self._read_handle ())
    return message_count
    
  def empty (self):
    maxsize, nextsize, message_count, timeout = wrapped (win32file.GetMailslotInfo, self._read_handle ())
    return message_count == 0
    
  def full (self):
    maxsize, nextsize, message_count, timeout = wrapped (win32file.GetMailslotInfo, self._read_handle ())
    return message_count == maxsize
  
  def get (self, block=True, timeout_ms=None):
    hMailslot = self._read_handle ()
    if timeout_ms is None:
      timeout_ms = self.timeout_ms
    if timeout_ms == -1:
      timeout = None
    else:
      timeout = timeout_ms / 1000.0
    
    t0 = time.time ()
    while True:
      maxsize, nextsize, message_count, default_timeout = wrapped (win32file.GetMailslotInfo, hMailslot)
      if message_count == 0:
        if block:
          if (timeout is not None) and (time.time () - t0) > timeout:
            raise x_mailslot_empty
          else:
            time.sleep (0.1)
        else:
          raise x_mailslot_empty
      else:
        hr, data = wrapped (win32file.ReadFile, hMailslot, nextsize, None)
        return data
    
  def get_nowait (self):
    return self.get (False, 0)
    
  def put (self, data):
    wrapped (win32file.WriteFile, self._write_handle (), data, None)
    
  def close (self):
    if self._hRead is not None:
      wrapped (win32file.CloseHandle, self._hRead)
    if self._hWrite is not None:
      wrapped (win32file.CloseHandle, self._hWrite)

class Event (core._WinSysObject):
  
  def __init__ (self, security=None, needs_manual_reset=False, initially_set=False, name=None):
    core._WinSysObject.__init__ (self)
    self.security = security
    self.needs_manual_reset = needs_manual_reset
    self.initially_set = initially_set
    self.name = name
    self._hEvent = None
  
  def as_string (self):
    return self.name or str (int (self._handle ()))
    
  def dumped (self, level=0):
    output = []
    output.append ("name: %s" % self.name or "anonymous")
    output.append ("needs_manual_reset: %s" % self.needs_manual_reset)
    output.append ("initially_set: %s" % self.initially_set)
    return utils.dumped ("\n".join (output), level)
  
  def pyobject (self):
    return self._handle ()
  
  def _handle (self):
    if self._hEvent is None:
      self._hEvent = wrapped (
        win32event.CreateEvent, 
        self.security, 
        self.needs_manual_reset, 
        self.initially_set, 
        self.name
      )
    return self._hEvent
  
  def pulse (self):
    wrapped (win32event.PulseEvent, self._handle ())
    
  def set (self):
    wrapped (win32event.SetEvent, self._handle ())
    
  def clear (self):
    wrapped (win32event.ResetEvent, self._handle ())
  reset = clear
    
  def wait (self, timeout_s=WAIT.INFINITE):
    if timeout_s == WAIT.INFINITE:
      timeout_ms = timeout_s
    else:
      timeout_ms = timeout_s * 1000.0
    result = wrapped (win32event.WaitForSingleObject, self._handle (), int (timeout_ms))
    if result == WAIT.TIMEOUT:
      return False
    else:
      return True
      
  def isSet (self):
    return self.wait (0)
    
  def __nonzero__ (self):
    return self.isSet ()
  
#
# Module-level convenience functions
#
def mailslot (mailslot, message_size=0, timeout_ms=-1):
  """factory function to return a Mailslot instance
  based on the name given. If the name is not a fully-qualified
  mailslot name (\\.\mailslot) then it is assumed to be on
  the local machine and is prefixed accordingly
  """
  if mailslot is None:
    return None
  elif isinstance (mailslot, Mailslot):
    return mailslot
  else:
    if not re.match (ur"\\\\[^\\]+\\mailslot\\", unicode (mailslot), re.UNICODE):
      mailslot = ur"\\.\mailslot\%s" % mailslot
    return Mailslot (mailslot, message_size, timeout_ms)

def event (name=None, initially_set=0, needs_manual_reset=0, security=None):
  return Event (security, needs_manual_reset, initially_set, name)

def any (handle_list, timeout_ms=WAIT.INFINITE):
  result = wrapped (win32event.WaitForMultipleObjects, handle_list, 0, timeout_ms)
  if result == WAIT.TIMEOUT:
    raise x_ipc_timeout ("Wait timed out", "any", 0)
  else:
    return handle_list[result - WAIT.OBJECT_0]

def all (handle_list, timeout_ms=WAIT.INFINITE):
  result = wrapped (win32event.WaitForMultipleObjects, handle_list, 1, timeout_ms)
  if result == WAIT.TIMEOUT:
    raise x_ipc_timeout ("Wait timed out", "all", 0)
  else:
    return handle_list[result - WAIT.OBJECT_0]
