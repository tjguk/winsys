import os
import csv
from winsys import event_logs, dialogs

def remote_events (computer, event_source, event_type_id):
  for event in event_logs.event_log (r"\\%s\system" % computer):
    if event.source_name.upper () == event_source and event.event_type == event_type_id:
      yield event
  
computer, event_source, (event_type_name, event_type_id) = dialogs.dialog (
  "Computer", 
  ("Computer Name", "."),
  ("Event Source", "DHCP"),
  ("Event Type", event_logs.EVENTLOG_TYPE.items ())
)

csv.writer (open ("dhcp.csv", "wb")).writerows (
  (event.record_number, event.time_generated, event.event_id, event.message) for
    event in remote_events (computer, event_source.upper (), event_type_id)
)

os.startfile ("dhcp.csv")
