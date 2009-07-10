# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys
import contextlib
import re
import struct

import winerror
import win32api
import win32event
import win32evtlog
import win32evtlogutil
import pywintypes

from winsys import accounts, constants, core, exc, registry, utils

EVENTLOG_READ = constants.Constants.from_pattern (u"EVENTLOG_*_READ", namespace=win32evtlog)
EVENTLOG_READ.doc ("Ways of reading event logs")
EVENTLOG_TYPE = constants.Constants.from_pattern (u"EVENTLOG_*_TYPE", namespace=win32evtlog)
EVENTLOG_TYPE.update (dict (
  AUDIT_FAILURE = win32evtlog.EVENTLOG_AUDIT_FAILURE,
  AUDIT_SUCCESS = win32evtlog.EVENTLOG_AUDIT_SUCCESS
))
EVENTLOG_TYPE.doc ("Types of records in event logs")

PyHANDLE = pywintypes.HANDLEType

DEFAULT_LOG_NAME = "Application"

class x_event_logs (exc.x_winsys):
  "Base exception for eventlog-specific exceptions"
  
WINERROR_MAP = {
  winerror.ERROR_ACCESS_DENIED : exc.x_access_denied
}
wrapped = exc.wrapper (WINERROR_MAP)

class _EventLogEntry (core._WinSysObject):
  """Internal class for convenient access to attributes of an event log
  record. Attributes are available as lowercase_with_underscore equivalents
  of their TitleCase counterparts and are converted to Python data types
  where appropriate, eg time_written is a datetime value and sid is
  an :class:`accounts.Principal` instance.
  
  Two _EventLogEntry instances compare equal if they have the same
  record number on the same event log on the same computer.
  """
  
  def __init__ (self, event_log_name, event_log_entry):
    self._event_log_name = event_log_name
    self._event_log_entry = event_log_entry
    self.record_number = event_log_entry.RecordNumber
    self.time_generated = utils.from_pytime (event_log_entry.TimeGenerated)
    self.time_written = utils.from_pytime (event_log_entry.TimeWritten)
    self.event_id = event_log_entry.EventID
    self.event_type = event_log_entry.EventType
    self.event_category = event_log_entry.EventCategory
    try:
      self.sid = accounts.principal (event_log_entry.Sid)
    except accounts.x_accounts:
      self.sid = None
    self.computer_name = event_log_entry.ComputerName
    self.source_name = event_log_entry.SourceName
    self.data = event_log_entry.Data
    self._message = None
    
  def as_string (self):
    return "%d - %s (%s)" % (self.record_number, self.source_name, EVENTLOG_TYPE.name_from_value (self.event_type))
    
  def __eq__ (self, other):
    return \
      self.computer_name == other.computer_name and \
      self._event_log_name == other._event_log_name and \
      self.record_number == other.record_number
  
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
      self._message = wrapped (win32evtlogutil.SafeFormatMessage, self._event_log_entry, self._event_log_name)
    return self._message
  message = property (_get_message)

class EventLog (core._WinSysObject):
  
  """An Event Log is a sequential database managed through API calls
  with a number of different Event Sources, against which events can
  be logged. The log can be read backwards (using the reversed () builtin)
  or forwards but only sequentially. 
  (We simulate random access by reading sequentially until a record is hit).
  
  You can use the builtin len () to determine the current size of
  this log (which may or may not correspond to the maximum record
  number). Item access is possible from either end by subscripting
  the log in the usual way. It should be noted that this uses iteration,
  forward or reverse as needed, so is not going to be that efficient
  except to find a few records at either end.
  
  Instances of this class are expected to be accessed via the 
  :func:`event_log` function.
  """
  
  REG_ROOT = r"\\%s\HKLM\SYSTEM\CurrentControlSet\Services\Eventlog"
  
  def __init__ (self, computer, name):
    core._WinSysObject.__init__ (self)
    self.computer = computer or "."
    self.name = name
    key = registry.registry (self.REG_ROOT % self.computer).get_key (self.name)
    if not key:
      raise x_not_found (None, "EventLog", r"\\%s\%s" % (self.computer, self.name))
    else:
      values = dict (key.values ())
      self.auto_backup_log_files = values.get ("AutoBackupLogFiles")
      self.display_name_file = values.get ("DisplayNameFile")
      self.display_name_id = values.get ("DisplayNameID")
      self.file = values.get ("File")
      self.max_size = values.get ("MaxSize")
      self.primary_module = values.get ("PrimaryModule")
      self.restrict_guest_access = values.get ("RestrictGuestAccess")
      self.retention = values.get ("Retention")
      self.sources = values.get ("Sources")
    self._handle = wrapped (win32evtlog.OpenEventLog, self.computer, self.name)
    
  def as_string (self):
    return r"%s\%s" % (self.computer, self.name)
      
  def dumped (self, level=0):
    output = []
    output.append (u"auto_backup_log_files: %s" % self.auto_backup_log_files)
    output.append (u"display_name_file: %s" % self.display_name_file)
    output.append (u"display_name_id: %s" % self.display_name_id)
    output.append (u"file: %s" % self.file)
    output.append (u"max_size: %s" % utils.size_as_mb (self.max_size))
    output.append (u"primary_module: %s" % self.primary_module)
    output.append (u"restrict_guest_access: %s" % self.restrict_guest_access)
    output.append (u"retention: %s" % utils.secs_as_string (self.retention))
    output.append (u"sources: %s" % utils.dumped_list (self.sources, level))
    return utils.dumped (u"\n".join (output), level)
  
  @contextlib.contextmanager
  def _temp_handle (self):
    """Internal, context-managed function to provide a working
    handle for the event log. You can't just open one at the
    beginning and work with it.
    """
    handle = wrapped (win32evtlog.OpenEventLog, self.computer, self.name)
    yield handle
    wrapped (win32evtlog.CloseEventLog, handle)
  
  def clear (self, save_to_filename=None):
    """Clear the event log, optionally saving out to an opaque file first,
    using the built-in functionality.
    """
    wrapped (win32evtlog.ClearEventLog, self._handle, unicode (save_to_filename))
    
  def __len__ (self):
    """Allow len () to return the number of records in the event log"""
    return wrapped (win32evtlog.GetNumberOfEventLogRecords, self._handle)
  
  def __getitem__ (self, index):
    """Allow the event log to be accessed by numeric index. An index of
    zero represents the oldest available record; -1 represents the latest
    available record.
    
    NB This is slow since it simply wraps an iterator in the appropriate
    direction. There is no way to find an arbitrary record in an event log.
    """
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
  
  def _iterator (self, flags):
    """Internal function to open a handle over the event log and iterate
    in either direction.
    """
    with self._temp_handle () as handle:
      while True:
        entries = wrapped (win32evtlog.ReadEventLog, handle, flags, 0)
        if entries:
          for entry in entries:
            yield _EventLogEntry (self, entry)
        else:
          raise StopIteration
  
  def __iter__ (self):
    """Return an iterator which traverses this event log lates record first"""
    return self._iterator (EVENTLOG_READ.FORWARDS | EVENTLOG_READ.SEQUENTIAL)
        
  def __reversed__ (self):
    """Return an iterator which traverses this event log oldest record first"""
    return self._iterator (EVENTLOG_READ.BACKWARDS | EVENTLOG_READ.SEQUENTIAL)
    
  def watcher (self):
    """(EXPERIMENTAL) Unsure if this will be of any use. In principle, you can ask for an event 
    to fire when a new record is written to this log. In practice, though, there's 
    no way of determining which record was added and you have to do some housekeeping 
    and work out what changed.
    
    Probably quite inefficient since it has to keep iterating backwards over the
    log every time to find the last record to match against. Does work, though.
    """
    TIMEOUT_SECS = 2
    hEvent = win32event.CreateEvent (None, 1, 0, None)
    
    iterator = iter (self)
    last_record = self[-1]
    for i in iterator:
      if i == last_record:
        break

    print "last record", i
    with self._temp_handle () as handle:
      wrapped (win32evtlog.NotifyChangeEventLog, self._handle, hEvent)
      while True:
        if win32event.WaitForSingleObject (hEvent, 1000 * TIMEOUT_SECS) != win32event.WAIT_TIMEOUT:
          print "not timedout"
          last_record = self[-1]
          print "last_record", last_record
          for i in iterator:
            yield i
            if i == last_record:
              break

  def log_event (self, source, *args, **kwargs):
    """Pass-through for :func:`log_event`"""
    log_event (source, *args, **kwargs)

class EventSource (core._WinSysObject):
  """An Event Source is an apparently necessary but in fact slightly unnecessary
  part of the event log mechanism. In principle, it represents a name and a DLL
  with a bunch of message ids in it. In practice, you can log an event with an
  unregistered event source and it will work quite happily although the event
  viewer won't be able to pick up the full message, only the inserted strings
  and the added data.
  
  Implemented here mostly for internal use in the :func:`log_event` function. NB We're
  using the convenience functions offered by win32evtlogutil, which make use of
  defaults built in to the win32event.pyd file. In the future we may implement
  our own .DLL builder.
  
  Instances of this class are expected to be accessed via the :func:`event_source`
  module-level function.
  """
  
  _keys = ['CategoryCount', 'CategoryMessageFile', 'EventMessageFile', 'ParameterMessageFile', 'TypesSupported']
  
  def __init__ (self, computer, log_name, source_name):
    core._WinSysObject.__init__ (self)
    self.computer = computer or "."
    self.log_name = log_name or DEFAULT_LOG_NAME
    self.name = source_name
    key = registry.registry (r"%s\%s\%s" % (EventLog.REG_ROOT % self.computer, self.log_name, self.name))
    if not key:
      raise x_not_found (None, "EventSource", r"\\%s\%s\%s" % (self.computer, self.log_name, self.name))
    self._handle = None
    values = dict ((name, value) for (name, value, type) in key.values ())
    types = dict ((name, type) for (name, value, type) in key.values ())
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
    return r"%s\%s\%s" % (self.computer, self.log_name, self.name)
  
  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append ("category_count: %s" % self.category_count)
    output.append ("category_message_file: %r" % self.category_message_file)
    output.append ("event_message_file: %r" % self.event_message_file)
    output.append ("parameter_message_file: %r" % self.parameter_message_file)
    output.append ("types_supported: %s" % EVENTLOG_TYPE.names_from_value (self.types_supported))
    return utils.dumped ("\n".join (output), level)
    
  #
  # Context manager to allow a handle for this event source to
  # be passed to the ReportEvent function in log_event (qv).
  #
  def __enter__ (self):
    self._handle = wrapped (win32evtlog.RegisterEventSource, self.computer, self.name) 
    return self._handle
    
  def __exit__ (self, *exc_info):
    wrapped (win32evtlog.DeregisterEventSource, self._handle)

  @classmethod
  def create (cls, name, log_name=DEFAULT_LOG_NAME):
    """Call the convenience functions to add a simple event source to
    the registry against a named event log (usually Application).
    Return the event source so you can log against it.
    
    :param name: name of the new event source
    :param log_name: name of the associated event log
    """
    win32evtlogutil.AddSourceToRegistry (appName=name, eventLogType=log_name)
    return cls ("", log_name, name)
    
  def delete (self):
    """Remove an event source from the registry. NB There is no particular
    security at work here: it's perfectly possible to remove someone else's
    event source.
    """
    win32evtlogutil.RemoveSourceFromRegistry (appName=self.name, eventLogType=self.log_name)
  
  def log_event (self, *args, **kwargs):
    """Pass-through to module-level :func:`log_event`"""
    log_event (self, *args, **kwargs)

#
# Module-level convenience functions
#
def event_logs (computer="."):
  """Simple iterator over all known event logs.
  """
  for key in registry.registry (EventLog.REG_ROOT % computer).keys ():
    yield EventLog (computer, key.name)

def event_log (log):
  ur"""Convenience function to return an :class:`EventLog` object representing
  one of the existing event logs. Will raise :exc:`x_not_found` if the event
  log does not exist.
  
  :param log: one of None, an :class:`EventLog` instance, or a [\\\\computer\\]name moniker
  """
  if log is None:
    return None
  elif isinstance (log, EventLog):
    return log
  else:
    computer, log_name = re.match (r"(?:\\\\([^\\]+)\\)?(.+)$", unicode (log), re.UNICODE).groups ()
    return EventLog (computer, log_name)

def event_sources (log_name=DEFAULT_LOG_NAME, computer="."):
  """Simple iterator over all the event sources for a named log
  """
  for key in registry.registry (EventLog.REG_ROOT % computer).get_key (log_name).keys ():
    yield EventSource (computer, log_name, key.name)
    
def event_source (source):
  r"""Convenience function to return an :class:`EventSource` object representing
  one of the existing event sources. Will raise :exc:`exceptions.x_not_found` if the event
  source does not exist.

  :param source: one of None, an :class:`EventSource` instance, or a [[\\\\computer]\\log\\]name moniker
  """
  if isinstance (source, EventSource):
    return source
  elif source is None:
    return None
  else:
    match = re.match (r"(?:\\\\([^\\]+)\\)?(?:([^\\]+)\\)?(.+)$", source, re.UNICODE)
    if match is None:
      raise x_event_logs (r"Event source must be of form [\\computer\]event_log\event_source")
    else:
      computer, log_name, source_name = match.groups ()
      return EventSource (computer or ".", log_name or DEFAULT_LOG_NAME, source_name)

def log_event (source, type="error", message=None, data=None, id=0, category=0, principal=core.UNSET):
  """Convenience function to log an event against an existing source.
  
  :param source: anything accepted by :func:`event_source`
  :param type: an :data:`EVENTLOG_TYPE`
  :param message: a string or list of strings
  :param data: a bytestring
  :param id: a number corresponding to the event message
  :param category: a number relevant to the event source
  :param principal: anything which :func:`accounts.principal` accepts [logged-on user]
  """
  type = EVENTLOG_TYPE.constant (type)
  principal = accounts.me () if principal is core.UNSET else accounts.principal (principal)
  if isinstance (message, basestring):
    message = [message]
  with event_source (source) as hLog:
    win32evtlog.ReportEvent (
      hLog,
      type,
      category,
      id,
      principal.pyobject (),
      message,
      data
    )

if __name__ == '__main__':
  pass
