from winsys import event_logs

for log in event_logs.event_logs ():
  print log
  for n_event, event in enumerate (reversed (log)):
    if n_event == 10: break
    print event.time_generated, event

  print