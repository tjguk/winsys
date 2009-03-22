# -*- coding: iso-8859-1 -*-
import marshal
import re
import time
import warnings

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

class x_mailslot_invalid_use (x_mailslot):
  pass

class x_mailslot_empty (x_mailslot):
  pass
  
class x_mailslot_message_too_big (x_mailslot):
  pass

class x_mailslot_message_too_complex (x_mailslot):
  pass
  
WINERROR_MAP = {
  winerror.ERROR_FILE_NOT_FOUND : x_not_found,
}
wrapped = wrapper (WINERROR_MAP, x_ipc)

class Mailslot (core._WinSysObject):
  """A mailslot is a mechanism for passing small datasets (up to about
  400 bytes) between machines in the same network. For transport and
  name resolution it uses NetBIOS so you can't, for example, use a
  machine's IP address when specifying the location of a mailslot.
  You can, however, use "*" in order to broadcast your message to
  all listening machines.
  
  A mailslot is either read-only or write-only. The typical case
  is that one machine starts up a reading mailslot, say for trace
  output, and all other machines write to that mailslot either by
  specifying the machine name directly or by broadcasting. This is
  particularly convenient as the writing machines have no need to
  determine where the trace-collecting mailslot is running or even
  if it is running at all.
  
  The format for mailslot names is \\<computer>\mailslot\<path>\<to>\<mailslot>
  The computer name can be "." for the local computer, a Windows
  computer name, a domain name, or an asterisk to indicate a broadcast. 
  It's not necessary to have a complex path for the mailslot but it is
  supported and could be used to segregate functionally similar
  mailslots on the same or different machines.
  
  This class deliberately wraps the mailslot API in a Python
  API which is plug-compatible with that of the Python Queue
  mechanism with the following notes:
  
  * A mailslot is either read-only or write-only. Generally,
    the first action taken on it determines which it is, although
    remote mailslots can only be written to so this is predetermined.
    
  * A mailslot can be context-managed so that it is opened and
    closed correctly regardless of any errors.
    
  * A mailslot is its own iterator (strictly: generator)
  """
  
  MAX_MESSAGE_SIZE = 420
  
  def __init__ (
    self, 
    name, 
    serialiser=(str, str), 
    message_size=0, 
    timeout_ms=-1, 
    *args, **kwargs
  ):
    """Set up a mailslot of the given name, which must be valid according to
    the Microsoft docs.
    
    serialiser : a pair of functions which will be used to 
    encode & decode data respectively. Typical serialisers
    are (str, str) and (marshal.dumps, marshal.loads).
    
    message_size : the maximum size of a message to this mailslot,
    up to the system-defined maximum of about 400 bytes if passing
    between computers. 
    
    timeout_ms : how many milliseconds to wait when reading from 
    this mailslot
    """
    core._WinSysObject.__init__ (self, *args, **kwargs)
    self.name = name
    self.serialiser = serialiser
    self.message_size = message_size
    self.timeout_ms = timeout_ms
    self._hRead = self._hWrite = None
    #
    # If the name is a local mailslot it could conceivably
    # be used for reading or for writing. If it is a
    # remote (including domain) mailslot, it can only
    # be written to.
    #
    if not name.startswith (r"\\."):
      self._hWrite = self._write_handle ()
      if self.message_size != 0 and self.message_size > self.MAX_MESSAGE_SIZE:
        warnings.warn (
          "You have specified a message size of %d for a remote mailslot."
          "Messages over %d in size will probably fail" % \
          (self.message_size, self.MAX_MESSAGE_SIZE)
        )
  
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
            time.sleep (0.001)
        else:
          raise x_mailslot_empty
      else:
        hr, data = wrapped (win32file.ReadFile, hMailslot, nextsize, None)
        serialiser_in, serialiser_out = self.serialiser
        return serialiser_out (data)
    
  def get_nowait (self):
    return self.get (False, 0)
    
  def put (self, data):
    serialiser_in, serialiser_out = self.serialiser    
    data = serialiser_in (data)
    if self.message_size and len (data) > self.message_size:
      raise x_mailslot_message_too_big (
        "Mailslot messages must be <= %d bytes" % self.message_size, 
        "%s.put" % self.__class__.__name__, 0
      )
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
def mailslot (mailslot, marshalled=True, message_size=0, timeout_ms=-1):
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
    if marshalled:
      serialiser = (marshal.dumps, marshal.loads)
    else:
      serialiser = (str, str)
    if not re.match (ur"\\\\[^\\]+\\mailslot\\", unicode (mailslot), re.UNICODE):
      mailslot = ur"\\.\mailslot\%s" % mailslot
    return Mailslot (mailslot, serialiser, message_size, timeout_ms)

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
