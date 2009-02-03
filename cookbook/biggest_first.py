from __future__ import with_statement
import os, sys
import threading
import time
import Queue
import urllib
from wsgiref.simple_server import make_server
from wsgiref.util import request_uri, application_uri, shift_path_info

from winsys import fs

def get_files (path, size_threshold, results):
  while True:
    for f in fs.flat (path, ignore_access_errors=True):
      try:
        if f.size > size_threshold:
          results.put (f)
      except:
        pass

class App (object):
  
  REFRESH_THRESHOLD = 1000
  SIZE_THRESHOLD = 1024 * 1024
  TOP_N_FILES = 50
   
  def __init__ (self, path):
    self.path = path
    self.files_queue = Queue.Queue ()
    self.files = set ()
    
    file_getter = threading.Thread (
      target=get_files, 
      args=(self.path, self.SIZE_THRESHOLD, self.files_queue)
    )
    file_getter.setDaemon (1)
    file_getter.start ()
  
  def __call__ (self, environ, start_response):
    path = shift_path_info (environ)
    if path.rstrip ("/") == "":
      start_response (
        "200 OK", 
        [
          ("Content-Type", "text/html; charset=utf-8"),
          ("Refresh", "60"),
        ]
      )
      return (d.encode ("utf8") + "\n" for d in self.handler ())
    else:      
      start_response ("404 Not Found", [("Content-Type", "text/plain")])
      return []

  def doc (self, files):
    title = "Top %d / %d files on %s over %dMb" % (self.TOP_N_FILES, len (files), self.path, self.SIZE_THRESHOLD / 1024.0 / 1024.0)
    doc = []
    doc.append (u"<html><head><title>%s</title>" % title)
    doc.append (u"""<style>
    body {font-family : verdana, arial, sans-serif;}
    p.updated {margin-bottom : 1em; font-style : italic;}
    thead tr {background-color : black; color : white; font-weight : bold;}
    table td {padding-right : 0.5em;}
    table td.filename {width : 72%;}
    </style>""")
    doc.append (u"</head><body>")
    doc.append (u"<h1>%s</h1>" % title)
    doc.append (u'<p class="updated">Last updated %s</p>' % time.asctime ())
    doc.append (u"<table><thead><tr><td>Filename</td><td>Size (Mb)</td><td>Updated</td></tr></thead>")
    for f in files[:self.TOP_N_FILES]:
      doc.append (u'<tr><td class="filename">%s</td><td class="size">%5.2f</td><td class="updated">%s</td>' % (f.filepath, f.size / 1024.0 / 1024.0, f.written_at))
    doc.append (u"</table>")
    doc.append (u"</body></html>")
    return doc

  def handler (self):
    def _key (f):
      return -f.size / time.mktime (f.written_at.timetuple ())

    for i in range (self.REFRESH_THRESHOLD):
      try:
        f = self.files_queue.get_nowait ()
        self.files.add (f)
      except Queue.Empty:
        break
    return self.doc (sorted (self.files, key=_key))
 
def run_browser ():
  import os
  os.startfile ("http://localhost:8000")

if __name__ == '__main__':
  try:
    path = sys.argv[1]
  except IndexError:
    path = "c:\\"
  threading.Timer (3.0, run_browser).start ()
  make_server ('', 8000, App (path)).serve_forever ()
