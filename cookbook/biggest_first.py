from __future__ import with_statement
import os, sys
import cgi
import threading
import time
import Queue
import urllib
import urlparse
from wsgiref.simple_server import make_server
from wsgiref.util import request_uri, application_uri, shift_path_info

from winsys import fs

def get_files (path, size_threshold_mb, results, stop_event):
  size_threshold = size_threshold_mb * 1024 * 1024
  for f in fs.flat (path, ignore_access_errors=True):
    if stop_event.is_set (): break
    try:
      if f.size > size_threshold:
        results.put (f)
    except fs.exceptions.x_winsys:
      continue

def watch_files (path, size_threshold_mb, results, stop_event):
  size_threshold = size_threshold_mb * 1024 * 1024
  watcher = fs.watch (path)
  while True:
    if stop_event.is_set (): break
    action, old_filename, new_filename = watcher.next ()
    if old_filename:
      old_file = fs.file (os.path.join (path, old_filename))
      if (not old_file) or (old_file and old_file.size > size_threshold):
        results.put (old_file)
    if new_filename and new_filename<> old_filename:
      new_file = fs.file (os.path.join (path, new_filename))
      if new_file and new_file.size > size_threshold:
        results.put (new_file)

class Path (object):
  
  def __init__ (self, path, size_threshold_mb):
    self._path = path
    self._size_threshold_mb = size_threshold_mb
    self._changes = Queue.Queue ()
    self._stop_event = threading.Event ()
    self._files = set ()
    
    file_getter = threading.Thread (
      target=get_files, 
      args=(path, size_threshold_mb, self._changes, self._stop_event)
    )
    file_getter.setDaemon (1)
    file_getter.start ()
    
    file_watcher = threading.Thread (
      target=watch_files,
      args=(path, size_threshold_mb, self._changes, self._stop_event)
    )
    file_watcher.setDaemon (1)
    file_watcher.start ()
    
  def __str__ (self):
    return "<Path: %s (%d files above %d Mb)>" % (self._path, len (self._files), self._size_threshold_mb)
  __repr__ = __str__

  def updated (self, refresh_threshold):
    for i in range (refresh_threshold):
      try:
        f = self._changes.get_nowait ()
        if f:
          self._files.add (f)
        else:
          self._files.discard (f)
      except Queue.Empty:
        break
    return self._files
    
  def finish (self):
    self._stop_event.set ()

class App (object):
  
  PATH = "C:\\"
  REFRESH_THRESHOLD = 1000
  SIZE_THRESHOLD_MB = 10
  TOP_N_FILES = 50
  REFRESH_SECS = 60
  
  def __init__ (self):
    self._paths_lock = threading.Lock ()
    self.paths = {}
  
  def doc (self, files, form):
    path = form.get ("path", self.PATH)
    top_n_files = int (form.get ("top_n_files", self.TOP_N_FILES))
    size_threshold_mb = int (form.get ("size_threshold_mb", self.SIZE_THRESHOLD_MB))
    title = "Top %d files on %s over %dMb" % (top_n_files, path, size_threshold_mb)
    doc = []
    doc.append (u"<html><head><title>%s</title>" % title)
    doc.append (u"""<style>
    body {font-family : verdana, arial, sans-serif;}
    p.updated {margin-bottom : 1em; font-style : italic;}
    table {width : 100%;}
    thead tr {background-color : black; color : white; font-weight : bold;}
    table td {padding-right : 0.5em;}
    table td.filename {width : 72%;}
    </style>""")
    doc.append (u"</head><body>")
    doc.append (u"<h1>%s</h1>" % title)
    doc.append (u'<p class="updated">Last updated %s</p>' % time.asctime ())
    doc.append (u"<table><thead><tr><td>Filename</td><td>Size (Mb)</td><td>Updated</td></tr></thead>")
    for f in files[:top_n_files]:
      try:
        doc.append (
          u'<tr><td class="filename">%s</td><td class="size">%5.2f</td><td class="updated">%s</td>' % (
            f.filepath.relative_to (path).lstrip (fs.seps), 
            f.size / 1024.0 / 1024.0, 
            f.written_at
          )
        )
      except fs.exceptions.x_winsys:
        pass
    doc.append (u"</table>")
    doc.append (u"</body></html>")
    return doc

  def handler (self, form):
    def _key (f):
      try:
        return -f.size / time.mktime (f.written_at.timetuple ())
      except fs.exceptions.x_winsys:
        return None

    path = form.get ("path", self.PATH)
    size_threshold_mb = int (form.get ("size_threshold_mb", self.SIZE_THRESHOLD_MB))
    refresh_threshold = int (form.get ("refresh_threshold", self.REFRESH_THRESHOLD))
    with self._paths_lock:
      path_handler = self.paths.setdefault (path, Path (path, size_threshold_mb))
      if path_handler._size_threshold_mb <> size_threshold_mb:
        path_handler.finish ()
        path_handler = self.paths[path] = Path (path, size_threshold_mb)
      files = sorted (path_handler.updated (refresh_threshold), key=_key)
    return self.doc (files, form)
 
  def __call__ (self, environ, start_response):
    path = shift_path_info (environ)
    if path.rstrip ("/") == "":
      form = dict ((k, v[0]) for (k, v) in urlparse.parse_qs (environ['QUERY_STRING']).items () if v)
      refresh_secs = form.get ("refresh_secs", self.REFRESH_SECS)
      start_response (
        "200 OK", 
        [
          ("Content-Type", "text/html; charset=utf-8"), 
          ("Refresh", "%s" % refresh_secs)
        ]
      )
      return (d.encode ("utf8") + "\n" for d in self.handler (form))
    else:      
      start_response ("404 Not Found", [("Content-Type", "text/plain")])
      return []

def run_browser ():
  import os
  os.startfile ("http://localhost:8000")

if __name__ == '__main__':
  #~ threading.Timer (3.0, run_browser).start ()
  make_server ('', 8000, App ()).serve_forever ()
