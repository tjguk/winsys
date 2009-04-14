from winsys import event_logs

try:
  source = event_logs.event_source ("WinSys")
except event_logs.x_not_found:
  source = event_logs.EventSource.create ("WinSys")

try:
  source.log_event (type="information", message="Testing")
finally:
  source.delete ()
