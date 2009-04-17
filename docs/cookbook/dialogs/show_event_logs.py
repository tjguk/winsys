from __future__ import with_statement
import os
import csv
from winsys import dialogs, event_logs

log_name, filename = dialogs.dialog (
  "Write event log to csv",
  ("Event log", list (event_logs.event_logs ())),
  ("CSV filename", ""),
)

namer = event_logs.EVENTLOG_TYPE.name_from_value
with open (filename, "wb") as f:
  csv.writer (f).writerows (
    (e.time_generated, e.source_name, namer (e.event_type), e.message) 
      for e in event_logs.event_log (log_name)
  )

os.startfile (filename)