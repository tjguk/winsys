"""Working example of the ReadDirectoryChanges API which will
 track changes made to a directory. Can either be run from a
 command-line, with a comma-separated list of paths to watch,
 or used as a module, either via the watch_path generator or
 via the Watcher threads, one thread per path.

Examples:
  watch_directory.py c:/temp,r:/images

or:
  import watch_directory
  for file_type, filename, action in watch_directory.watch_path ("c:/temp"):
    print filename, action

or:
  import watch_directory
  import Queue
  file_changes = Queue.Queue ()
  for pathname in ["c:/temp", "r:/goldent/temp"]:
    watch_directory.Watcher (pathname, file_changes)

  while 1:
    file_type, filename, action = file_changes.get ()
    print file_type, filename, action
"""
from __future__ import generators
import os, sys
import atexit
from datetime import datetime
import Queue
import threading
import time

import win32file
import win32con

from winsys import fs

ACTIONS = {
  1 : "Created",
  2 : "Deleted",
  3 : "Updated",
  4 : "Renamed to something",
  5 : "Renamed from something"
}

def watch_path (path_to_watch, include_subdirectories=False):
  FILE_LIST_DIRECTORY = 0x0001
  hDir = win32file.CreateFile (
    path_to_watch,
    FILE_LIST_DIRECTORY,
    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
    None,
    win32con.OPEN_EXISTING,
    win32con.FILE_FLAG_BACKUP_SEMANTICS,
    None
  )
  while True:
    results = win32file.ReadDirectoryChangesW (
      hDir,
      1024,
      include_subdirectories,
       win32con.FILE_NOTIFY_CHANGE_SIZE | win32con.FILE_NOTIFY_CHANGE_FILE_NAME,
      None,
      None
    )
    for action, file in results:
      full_filename = os.path.join (path_to_watch, file)
      if not os.path.exists (full_filename):
        file_type = "<deleted>"
      elif os.path.isdir (full_filename):
        file_type = 'folder'
      else:
        file_type = 'file'
      yield (file_type, full_filename, ACTIONS.get (action, "Unknown"))

class Watcher (threading.Thread):

  def __init__ (self, path_to_watch, results_queue, **kwds):
    threading.Thread.__init__ (self, **kwds)
    self.setDaemon (1)
    self.path_to_watch = path_to_watch
    self.results_queue = results_queue
    self.start ()

  def run (self):
    for result in watch_path (self.path_to_watch, True):
      self.results_queue.put (result)

def sizer (requests_queue, results_queue):
  while True:
    request = requests_queue.get ()
    if request is None:
      print "Stopping..."
      break
    else:
      results_queue.put ((request, sum (f.size for f in fs.flat (request))))

def stop_sizers (sizer_requests, n_sizers):
  for n in range (n_sizers):
    sizer_requests.put (None)

if __name__ == '__main__':
  """If run from the command line, use the thread-based
   routine to watch the current directory (default) or
   a list of directories specified on the command-line
   separated by commas, eg

   watch_directory.py c:/temp,c:/
  """
  PATH_TO_WATCH = "."
  N_SIZERS = 5
  try: 
    path_to_watch = sys.argv[1] or PATH_TO_WATCH
  except IndexError: 
    path_to_watch = PATH_TO_WATCH
  path_to_watch = os.path.abspath (path_to_watch)


  sizer_requests = Queue.Queue ()
  sizer_results = Queue.Queue ()
  sizers = [threading.Thread (target=sizer, args=(sizer_requests, sizer_results)) for _ in range (N_SIZERS)]
  for sizer in sizers:
    sizer.start ()

  try:
    last_updated = {}
    print "Watching %s at %s" % (path_to_watch, time.asctime ())
    files_changed = Queue.Queue ()
    Watcher (path_to_watch, files_changed)

    while True:
      top_level_dirs = set ()
      while True:
        try:
          file_type, filename, action = files_changed.get_nowait ()
          top_level_dirs.add (filename[len (path_to_watch):].split (os.sep)[1])
        except Queue.Empty:
          break
          
      for dir in top_level_dirs:
        if (datetime.now () - last_updated.get (dir, datetime.min)).seconds > 60:
          print "Requesting size of", os.path.abspath (dir)
          sizer_requests.put (os.path.abspath (dir))
          
      while True:
        try:
          dir, size = sizer_results.get_nowait ()
        except Queue.Empty:
          break
        else:
          print dir, "=>", size
      
      time.sleep (10)
      
  finally:
    stop_sizers (sizer_requests, len (sizers))
