import sys
from nose.tools import *
import winerror
import win32api
import win32con
import win32evtlog
import win32security
import pywintypes
import uuid

from winsys import event_logs, registry, utils

registry_root = registry.registry (r"HKLM\SYSTEM\CurrentControlSet\Services\Eventlog")

LOG_NAME = event_logs.DEFAULT_LOG_NAME
GUID = "_winsys-%s" % uuid.uuid1 ()

#
# Fixtures
#
def setup_source ():
  event_logs.EventSource.create (GUID, LOG_NAME)

def teardown_source ():
  event_logs.event_source (r"%s\%s" % (LOG_NAME, GUID)).delete ()

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

#
# Event Source
#
def test_create_source ():
  log_name = "System"
  guid = "_winsys-test_create_source-%s" % uuid.uuid1 ()
  try:
    source = event_logs.EventSource.create (guid, log_name)
    assert_true (registry_root + log_name + guid)
  except:
    raise
  else:
    source.delete ()
    assert_false (registry_root + log_name + guid)

def test_create_source_at_default ():
  guid = "_winsys-test_create_source_at_default-%s" % uuid.uuid1 ()
  try:
    source = event_logs.EventSource.create (guid)
    assert_true (registry_root + event_logs.DEFAULT_LOG_NAME + guid)
  except:
    raise
  else:
    source.delete ()
    assert_false (registry_root + event_logs.DEFAULT_LOG_NAME + guid)

def test_event_sources ():
  log_name = "System"
  assert_equals (
    set (s.name for s in event_logs.event_sources (log_name)),
    set (r.name for r in registry_root + log_name)
  )
  assert_true (all (isinstance (s, event_logs.EventSource) for s in event_logs.event_sources (log_name)))

def test_event_source_from_event_source ():
  for s in event_logs.event_sources ():
    assert_true (isinstance (s, event_logs.EventSource))
    assert_true (event_logs.event_source (s) is s)
    break

def test_event_source_from_none ():
  assert_true (event_logs.event_source (None) is None)

@raises (event_logs.x_event_logs)
def test_event_source_from_bad_string ():
  event_logs.event_source ("")

@with_setup (setup_source, teardown_source)
def test_event_source_from_good_string ():
  assert_true (
    isinstance (
      event_logs.event_source (r"%s\%s" % (LOG_NAME, GUID)),
      event_logs.EventSource
    )
  )

@with_setup (setup_source, teardown_source)
def test_event_source_from_good_string_default_log ():
  assert_true (
    isinstance (
      event_logs.event_source (GUID),
      event_logs.EventSource
    )
  )

@with_setup (setup_source, teardown_source)
def test_event_source_as_string ():
  assert_true (event_logs.event_source (GUID).as_string ())

@with_setup (setup_source, teardown_source)
def test_event_source_log_event ():
  event_logs.event_source (GUID).log_event (data=GUID)
  for event in yield_logs ():
    if event.SourceName == GUID and event.Data == GUID:
      assert_true (True)
      break
  else:
    assert_true (False)

#
# Event logs
#
def test_event_logs ():
  assert_equals (
    set (s.name for s in event_logs.event_logs ()),
    set (r.name for r in registry_root.keys ())
  )
  assert_true (all (isinstance (s, event_logs.EventLog) for s in event_logs.event_logs ()))

def test_event_log_from_event_log ():
  for l in event_logs.event_logs ():
    assert_true (isinstance (l, event_logs.EventLog))
    assert_true (event_logs.event_log (l) is l)
    break

def test_event_log_from_none ():
  assert_true (event_logs.event_log (None) is None)

@raises (event_logs.x_event_logs)
def test_event_log_from_bad_string ():
  event_logs.event_log  ("")

def test_event_log_from_good_string ():
  assert_true (
    isinstance (
      event_logs.event_log (LOG_NAME),
      event_logs.EventLog
    )
  )

def test_event_log_clear_no_save ():
  log_name = "Internet Explorer"
  source_name = "_winsys-%s" % uuid.uuid1 ()
  source = event_logs.EventSource.create (source_name, log_name)
  log = event_logs.event_log (log_name)
  hLog = win32evtlog.OpenEventLog (None, log_name)
  try:
    log.log_event (source, message="hello")
    assert_not_equals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
    log.clear ()
    assert_equals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
  finally:
    win32evtlog.CloseEventLog (hLog)
    source.delete ()

def test_event_log_clear_with_save ():
  log_name = "Internet Explorer"
  source_name = "_winsys-%s" % uuid.uuid1 ()
  source = event_logs.EventSource.create (source_name, log_name)
  log = event_logs.event_log (log_name)
  hLog = win32evtlog.OpenEventLog (None, log_name)
  try:
    log.log_event (source, message="hello")
    assert_not_equals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
    log.clear ()
    assert_equals (win32evtlog.GetNumberOfEventLogRecords (hLog), 0)
  finally:
    win32evtlog.CloseEventLog (hLog)
    source.delete ()

#
# Module-level functions
#
@with_setup (setup_source, teardown_source)
def test_log_event ():
  event_logs.log_event ("%s\\%s" % (LOG_NAME, GUID), data=GUID)
  for event in yield_logs ():
    if event.SourceName == GUID and event.Data == GUID:
      assert_true (True)
      break
  else:
    assert_true (False)

if __name__ == "__main__":
  import nose, sys
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
