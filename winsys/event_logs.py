# -*- coding: iso-8859-1 -*-
import os, sys
import contextlib
import operator
import re
import socket
import struct

import winerror
import win32api
import win32evtlog
import win32evtlogutil
import pywintypes

from winsys import core, utils, registry, accounts
from winsys.constants import *
from winsys.exceptions import *

PyHANDLE = pywintypes.HANDLEType

class x_event_logs (x_winsys):
  pass
  
WINERROR_MAP = {
  winerror.ERROR_ACCESS_DENIED : x_access_denied
}
wrapped = wrapper (WINERROR_MAP)

class _EventLogEntry (core._WinSysObject):
  
  def __init__ (self, event_log, event_log_entry):
    self._event_log = event_log
    self._event_log_entry = event_log_entry
    self.record_number = event_log_entry.RecordNumber
    self.time_generated = utils.from_pytime (event_log_entry.TimeGenerated)
    self.time_written = utils.from_pytime (event_log_entry.TimeWritten)
    self.event_id = event_log_entry.EventID
    self.event_type = event_log_entry.EventType
    self.event_category = event_log_entry.EventCategory
    self.sid = accounts.principal (event_log_entry.Sid)
    self.computer_name = event_log_entry.ComputerName
    self.source_name = event_log_entry.SourceName
    self.data = event_log_entry.Data
    self._message = None
    
  def as_string (self):
    return "%d - %s (%s)" % (self.record_number, self.source_name, EVENTLOG_TYPE.name_from_value (self.event_type))
  
  def dumped (self, level=0):
    output = []
    output.append (u"record_number: %s" % self.record_number)
    output.append (u"time_generated: %s" % self.time_generated)
    output.append (u"time_written: %s" % self.time_written)
    output.append (u"event_id: %s" % self.event_id)
    output.append (u"source_name: %s" % self.source_name)
    output.append (u"event_type: %s" % EVENTLOG_TYPE.name_from_value (self.event_type))
    output.append (u"event_category: %s" % self.event_category)
    output.append (u"sid: %s" % self.sid)
    output.append (u"computer_name: %s" % self.computer_name)
    output.append (u"data: %s" % repr (self.data))
    output.append (u"message: %s" % self.message)
    return utils.dumped (u"\n".join (output), level)
  
  def _get_message (self):
    if self._message is None:
      self._message = wrapped (win32evtlogutil.SafeFormatMessage, self._event_log_entry, self._event_log.name)
    return self._message
  message = property (_get_message)

class EventLog (core._WinSysObject):
  
  def __init__ (self, computer, name):
    core._WinSysObject.__init__ (self)
    self.computer = computer
    self.name = name
    self._handle = wrapped (win32evtlog.OpenEventLog, self.computer, self.name)
    
  def as_string (self):
    return "%s\\%s" % (self.computer, self.name)
  
  @contextlib.contextmanager
  def _temp_handle (self):
    handle = wrapped (win32evtlog.OpenEventLog, self.computer, self.name)
    yield handle
    wrapped (win32evtlog.CloseEventLog, handle)
  
  def clear (self, save_to_filename=None):
    wrapped (win32evtlog.ClearEventLog, self._handle, save_to_filename)
    
  def __len__ (self):
    return wrapped (win32evtlog.GetNumberOfEventLogRecords, self._handle)
  
  def __getitem__ (self, index):
    with self._temp_handle () as handle:
      if index >= 0:
        record_number = wrapped (win32evtlog.GetOldestEventLogRecord, handle) + index
        direction = EVENTLOG_READ.FORWARDS
      else:
        record_number = wrapped (win32evtlog.GetOldestEventLogRecord, handle) + len (self) + index
        direction = EVENTLOG_READ.BACKWARDS
      
      for entry in wrapped (
        win32evtlog.ReadEventLog,
        handle,
        EVENTLOG_READ.SEEK | direction,
        record_number
      ):
        return _EventLogEntry (self, entry)
  
  def iterator (self, flags):
    with self._temp_handle () as handle:
      while True:
        entries = wrapped (win32evtlog.ReadEventLog, handle, flags, 0)
        if entries:
          for entry in entries:
            yield _EventLogEntry (self, entry)
        else:
          raise StopIteration
  
  def __iter__ (self):
    return self.iterator (EVENTLOG_READ.FORWARDS | EVENTLOG_READ.SEQUENTIAL)
        
  def __reversed__ (self):
    return self.iterator (EVENTLOG_READ.BACKWARDS | EVENTLOG_READ.SEQUENTIAL)
    
  def watch (self, hEvent):
    wrapped (win32evtlog.NotifyChangeEventLog, self._handle, hEvent)

class EventSource (core._WinSysObject):
  
  _keys = ['CategoryCount', 'CategoryMessageFile', 'EventMessageFile', 'ParameterMessageFile', 'TypesSupported']
  
  def __init__ (self, computer, registry_key):
    core._WinSysObject.__init__ (self)
    self.computer = computer
    self.name = registry_key.name
    self._handle = None
    values = dict ((name, value) for (name, value, type) in registry_key.values ())
    types = dict ((name, type) for (name, value, type) in registry_key.values ())
    self.category_count = values.get ("CategoryCount")
    self.category_message_file = values.get ("CategoryMessageFile")
    self.event_message_file = values.get ("EventMessageFile")
    self.parameter_message_file = values.get ("ParameterMessageFile")
    types_supported = values.get ("TypesSupported") or 0
    #
    # This is messy because, although TypeSupported is specified
    # as a DWORD and constitutes a set of flags, it seems to be
    # implemented in any number of ingenious ways, including
    # binary data representing a number and a string representing
    # the hexadecimal value of the flags.
    #
    try:
      self.types_supported = int (types_supported or 0)
    except ValueError:
      types_type = types.get ("TypesSupported")
      if types_type == registry.REGISTRY_VALUE_TYPE.REG_SZ:
        if types_supported.startswith ("0x"):
          self.types_supported = int (types_supported, 16)
        else:
          self.types_supported = int (types_supported, 10)
      elif types_type == registry.REGISTRY_VALUE_TYPE.REG_BINARY:
        self.types_supported, = struct.unpack ("L", types_supported)
      else:
        raise x_event_logs (None, None, "Can't determine types supported")
    
  def as_string (self):
    return "%s\\%s" % (self.computer, self.name)
  
  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append ("category_count: %s" % self.category_count)
    output.append ("category_message_file: %r" % self.category_message_file)
    output.append ("event_message_file: %r" % self.event_message_file)
    output.append ("parameter_message_file: %r" % self.parameter_message_file)
    output.append ("types_supported: %s" % EVENTLOG_TYPE.names_from_value (self.types_supported))
    return utils.dumped ("\n".join (output), level)
    
  def __enter__ (self):
    self._handle = wrapped (win32evtlog.RegisterEventSource, self.computer, self.name) 
    return self._handle
    
  def __exit__ (self):
    wrapped (win32evtlog.DeregisterEventSource, self._handle)
  
#
# Module-level convenience functions
#
def event_logs (computer=None):
  if computer:
    prefix = r"\\%s" % computer
  else:
    prefix = ""
  for key in registry.key (prefix + r"\HKLM\SYSTEM\ControlSet001\Services\Eventlog").keys ():
    yield EventLog (computer, key.name)

def event_log (event_log):
  if event_log is None:
    return None
  elif isinstance (event_log, EventLog):
    return event_log
  else:
    computer, name = re.match (r"(?:\\\\([^\\]+)\\)?(\w+)", event_log, re.UNICODE).groups ()
    return EventLog (computer, name)

def event_sources (event_log_name, computer=None):
  if computer:
    prefix = r"\\%s" % computer
  else:
    prefix = ""
  for key in registry.key (prefix + r"\HKLM\SYSTEM\CurrentControlSet\Services\Eventlog\%s" % (event_log_name)).keys ():
    yield EventSource (computer, key)
    
def event_source (moniker):
  match = re.match (r"(?:\\\\([^\\]+)\\)?((?:\w|\s)+)\\((?:\w|\s)+)", moniker, re.UNICODE)
  if match is None:
    raise x_event_logs (r"Event source must be of form [\\computer\]event_log\event_source")
  else:
    computer, event_log_name, event_source_name = match.groups ()
    if computer:
      prefix = r"\\%s" % computer
    else:
      prefix = ""
    suffix = r"HKLM\SYSTEM\CurrentControlSet\Services\Eventlog\%s\%s" % (event_log_name, event_source_name)
    key = registry.key (prefix + "\\" + suffix)
    if key:
      return EventSource (computer, key)
    else:
      raise x_not_found (None, None, moniker)

if __name__ == '__main__':
  pass
