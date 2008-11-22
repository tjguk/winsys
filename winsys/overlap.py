import os, sys

import pywintypes
import win32file
import win32event
import win32con
import ntsecuritycon

overlapped = pywintypes.OVERLAPPED ()
overlapped.hEvent = win32event.CreateEvent (None, 0, 0, None)

hDir = win32file.CreateFile (
  "c:/temp",
  ntsecuritycon.FILE_LIST_DIRECTORY,
  win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
  None,
  win32con.OPEN_EXISTING,
  win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED,
  None
)
buffer = win32file.AllocateReadBuffer (8192)
while True:
  print "#0", win32file.ReadDirectoryChangesW (hDir, buffer, True, win32con.FILE_NOTIFY_CHANGE_FILE_NAME, overlapped)
  print "#1"
  rc = win32event.WaitForSingleObject (overlapped.hEvent, 1000)
  print "#2", rc
  if rc == win32event.WAIT_OBJECT_0:
    n_bytes = win32file.GetOverlappedResult (hDir, overlapped, True)
    if n_bytes:
      print win32file.FILE_NOTIFY_INFORMATION (buffer, n_bytes)
    else:
      break
