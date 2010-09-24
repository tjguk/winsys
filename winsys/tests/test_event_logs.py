import sys
import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0
import uuid

import winerror
import win32api
import win32con
import win32evtlog
import win32security
import pywintypes

from winsys import event_logs, registry, utils

registry_root = registry.registry (r"HKLM\SYSTEM\CurrentControlSet\Services\Eventlog")

LOG_NAME = event_logs.DEFAULT_LOG_NAME
GUID = "_winsys-%s" % uuid.uuid1 ()

#
# Utility functions
#
def yield_logs (computer=None, log_name=LOG_NAME):
  hLog = win32evtlog.OpenEventLog (computer, log_name)
  try:
    while True:
      entries = win32evtlog.ReadEventLog (
        hLog,
        win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
        0
      )
      if entries:
        for entry in entries:
          yield entry
      else:
        break
  finally:
    win32evtlog.CloseEventLog (hLog)

#
# TESTS
#

class TestEventLogs (unittest.TestCase):

  #
  # Fixtures
  #
  def setUp (self):
    event_logs.EventSource.create (GUID, LOG_NAME)

  def tearDown (self):
    event_logs.event_source (r"%s\%s" % (LOG_NAME, GUID)).delete ()

  #
  # Event Source
  #
  def test_create_source (self):
    log_name = "System"
    guid = "_winsys-test_create_source-%s" % uuid.uuid1 ()
    try:
      source = event_logs.EventSource.create (guid, log_name)
      self.assertTrue (registry_root + log_name + guid)
    except:
      raise
    else:
      source.delete ()
      self.assertFalse (bool (registry_root + log_name + guid))

  def test_create_source_at_default (self):
    guid = "_winsys-test_create_source_at_default-%s" % uuid.uuid1 ()
    try:
      source = event_logs.EventSource.create (guid)
      self.assertTrue (registry_root + event_logs.DEFAULT_LOG_NAME + guid)
    except:
      raise
    else:
      source.delete ()
      self.assertFalse (bool (registry_root + event_logs.DEFAULT_LOG_NAME + guid))

  def test_event_sources (self):
    log_name = "System"
    self.assertEquals (
      set (s.name for s in event_logs.event_sources (log_name)),
      set (r.name for r in registry_root + log_name)
    )
    self.assertTrue (all (isinstance (s, event_logs.EventSource) for s in event_logs.event_sources (log_name)))

  def test_event_source_from_event_source (self):
    for s in event_logs.event_sources ():
      self.assertTrue (isinstance (s, event_logs.EventSource))
      self.assertTrue (event_logs.event_source (s) is s)
      break

  def test_event_source_from_none (self):
    self.assertTrue (event_logs.event_source (None) is None)

  def test_event_source_from_bad_string (self):
    with self.assertRaises (event_logs.x_event_logs):
      event_logs.event_source ("")

  def test_event_source_from_good_string (self):
    self.assertTrue (
      isinstance (
        event_logs.event_source (r"%s\%s" % (LOG_NAME, GUID)),
        event_logs.EventSource
      )
    )

  def test_event_source_from_good_string_default_log (self):
    self.assertTrue (
      isinstance (
        event_logs.event_source (GUID),
        event_logs.EventSource
      )
    )

  def test_event_source_as_string (self):
    self.assertTrue (event_logs.event_source (GUID).as_string ())

  def test_event_source_log_event (self):
    data = str (GUID).encode ("utf8")
    event_logs.event_source (GUID).log_event (data=data)
    for event in yield_logs ():
      if event.SourceName == GUID and event.Data == data:
        self.assertTrue (True)
        break
    else:
      self.assertTrue (False)

  #
  # Event logs
  #
  def test_event_logs (self):
    self.assertEquals (
      set (s.name for s in event_logs.event_logs ()),
      set (r.name for r in registry_root.keys ())
    )
    self.assertTrue (all (isinstance (s, event_logs.EventLog) for s in event_logs.event_logs ()))

  def test_event_log_from_event_log (self):
    for l in event_logs.event_logs ():
      self.assertTrue (isinstance (l, event_logs.EventLog))
      self.assertTrue (event_logs.event_log (l) is l)
      break

  def test_event_log_from_none (self):
    self.assertTrue (event_logs.event_log (None) is None)

  def test_event_log_from_bad_string (self):
    with self.assertRaises (event_logs.x_event_logs):
      event_logs.event_log  ("")

  def test_event_log_from_good_string (self):
    self.assertTrue (
      isinstance (
        event_logs.event_log (LOG_NAME),
        event_logs.EventLog
      )
    )

  def test_event_log_clear_no_save (self):
    log_name = "Internet Explorer"
    source_name = "_winsys-%s" % uuid.uuid1 ()
    source = event_logs.EventSource.create (source_name, log_name)
    log = event_logs.event_log (log_name)
    hLog = win32evtlog.OpenEventLog (None, log_name)
    try:
      log.log_event (source, message="hello")
      self.assertNotEquals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
      log.clear ()
      self.assertEquals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
    finally:
      win32evtlog.CloseEventLog (hLog)
      source.delete ()

  def test_event_log_clear_with_save (self):
    log_name = "Internet Explorer"
    source_name = "_winsys-%s" % uuid.uuid1 ()
    source = event_logs.EventSource.create (source_name, log_name)
    log = event_logs.event_log (log_name)
    hLog = win32evtlog.OpenEventLog (None, log_name)
    try:
      log.log_event (source, message="hello")
      self.assertNotEquals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
      log.clear ()
      self.assertEquals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
    finally:
      win32evtlog.CloseEventLog (hLog)
      source.delete ()

  #
  # Module-level functions
  #
  def test_log_event (self):
    data = str (GUID).encode ("utf8")
    event_logs.log_event ("%s\\%s" % (LOG_NAME, GUID), data=data)
    for event in yield_logs ():
      if event.SourceName == GUID and event.Data == data:
        self.assertTrue (True)
        break
    else:
      self.assertTrue (False)

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
