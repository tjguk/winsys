"""Run a simple web server which responds to requests to monitor a directory
tree and identify files over a certain size threshold. The directory is
scanned to pick up the current situation and then monitored for new / removed
files. By default, the page auto-refreshes every 60 seconds and shows the
top 50 files ordered by size.
"""
from __future__ import with_statement
import os, sys
import cgi
import datetime
import operator
import socket
import threading
import time
import traceback
import Queue
import urllib
import urlparse
from wsgiref.simple_server import make_server
from wsgiref.util import shift_path_info
import win32timezone

import error_handler
from winsys import core, fs, misc
print "Logging to", core.log_filepath

def deltastamp (delta):

  def pluralise (base, n):
    if n > 1:
      return "%d %ss" % (n, base)
    else:
      return "%d %s" % (n, base)

  if delta > datetime.timedelta (0):
    output_format = "%s ago"
  else:
    output_format = "in %s"

  days = delta.days
  if days != 0:
    wks, days = divmod (days, 7)
    if wks > 0:
      if wks < 9:
        output = pluralise ("wk", wks)
      else:
        output = pluralse ("mth", int (round (1.0 * wks / 4.125)))
    else:
      output = pluralise ("day", days)
  else:
    mins, secs = divmod (delta.seconds, 60)
    hrs, mins = divmod (mins, 60)
    if hrs > 0:
      output = pluralise ("hr", hrs)
    elif mins > 0:
      output = pluralise ("min", mins)
    else:
      output = pluralise ("sec", secs)

  return output_format % output

class x_stop_exception (Exception):
  pass

def get_files (path, size_threshold_mb, results, stop_event):
  """Intended to run inside a thread: scan the contents of
  a tree recursively, pushing every file which is at least
  as big as the size threshold onto a results queue. Stop
  if the stop_event is set.
  """
  size_threshold = size_threshold_mb * 1024 * 1024
  root = fs.dir (path)
  top_level_folders = sorted (root.dirs (), key=operator.attrgetter ("written_at"), reverse=True)
  try:
    for tlf in top_level_folders:
      for f in tlf.flat (ignore_access_errors=True):
        if stop_event.isSet ():
          print "stop event set"
          raise x_stop_exception
        try:
          if f.size > size_threshold:
            results.put (f)
        except fs.exc.x_winsys:
          continue
  except x_stop_exception:
    return

def watch_files (path, size_threshold_mb, results, stop_event):
  """Intended to run inside a thread: monitor a directory tree
  for file changes. Convert the changed files to fs.File objects
  and push then onto a results queue. Stop if the stop_event is set.
  """
  size_threshold = size_threshold_mb * 1024 * 1024
  BUFFER_SIZE = 8192
  MAX_BUFFER_SIZE = 1024 * 1024

  #
  # The double loop is because the watcher process
  # can fall over with an internal which is (I think)
  # related to a small buffer size. If that happens,
  # restart the process with a bigger buffer up to a
  # maximum size.
  #
  buffer_size = BUFFER_SIZE
  while True:
    watcher = fs.watch (path, True, buffer_size=buffer_size)

    while True:
      if stop_event.isSet (): break
      try:
        action, old_file, new_file = watcher.next ()
        core.warn ("Monitored: %s - %s => %s" % (action, old_file, new_file))
        if old_file is not None:
          if (not old_file) or (old_file and old_file.size > size_threshold):
            results.put (old_file)
        if new_file is not None and new_file <> old_file:
          if new_file and new_file.size > size_threshold:
            results.put (new_file)
      except fs.exc.x_winsys:
        pass
      except RuntimeError:
        try:
          watcher.stop ()
        except:
          pass
        buffer_size = min (2 * buffer_size, MAX_BUFFER_SIZE)
        print "Tripped up on a RuntimeError. Trying with buffer of", buffer_size

class Path (object):
  """Keep track of the files and changes under a particular
  path tree. No attempt is made to optimise the cases where
  one tree is contained within another.

  When the Path is started, it kicks of two threads: one to
  do a complete scan; the other to monitor changes. Both
  write back to the same results queue which is the basis
  for the set of files which will be sorted and presented
  on the webpage.

  For manageability, the files are pulled off the queue a
  chunk at a time (by default 1000).
  """

  def __init__ (self, path, size_threshold_mb, n_files_at_a_time):
    self._path = path
    self._size_threshold_mb = size_threshold_mb
    self._n_files_at_a_time = n_files_at_a_time
    self._changes = Queue.Queue ()
    self._stop_event = threading.Event ()
    self._files = set ()

    self.file_getter = threading.Thread (
      target=get_files,
      args=(path, size_threshold_mb, self._changes, self._stop_event)
    )
    self.file_getter.setDaemon (1)
    self.file_getter.start ()

    self.file_watcher = threading.Thread (
      target=watch_files,
      args=(path, size_threshold_mb, self._changes, self._stop_event)
    )
    self.file_watcher.setDaemon (1)
    self.file_watcher.start ()

  def __str__ (self):
    return "<Path: %s (%d files above %d Mb)>" % (self._path, len (self._files), self._size_threshold_mb)
  __repr__ = __str__

  def updated (self):
    """Pull at most _n_files_at_a_time files from the queue. If the
    file exists, add it to the set (which will, of course, ignore
    duplicates). If it doesn't exist, remove it from the set, ignoring
    the case where it isn't there to start with.
    """
    for i in range (self._n_files_at_a_time):
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

  def status (self):
    status = []
    if self.file_getter.isAlive ():
      status.append ("Scanning")
    if self.file_watcher.isAlive ():
      status.append ("Monitoring")
    return " & ".join (status)

class App (object):
  """The controlling WSGI app. On each request, it looks up the
  path handler which corresponds to the path form variable. It then
  pulls any new entries and displays them according to the user's
  parameters.
  """

  PATH = ""
  N_FILES_AT_A_TIME = 1000
  SIZE_THRESHOLD_MB = 100
  TOP_N_FILES = 50
  REFRESH_SECS = 60
  HIGHLIGHT_DAYS = 0
  HIGHLIGHT_HRS = 12
  HIGHLIGHT_MINS = 0

  def __init__ (self):
    self._paths_lock = threading.Lock ()
    self.paths = {}
    self._paths_accessed = {}

  def doc (self, files, status, form):
    path = form.get ("path", self.PATH)
    top_n_files = int (form.get ("top_n_files", self.TOP_N_FILES) or 0)
    size_threshold_mb = int (form.get ("size_threshold_mb", self.SIZE_THRESHOLD_MB) or 0)
    refresh_secs = int (form.get ("refresh_secs", self.REFRESH_SECS) or 0)
    highlight_days = int (form.get ("highlight_days", self.HIGHLIGHT_DAYS) or 0)
    highlight_hrs = int (form.get ("highlight_hrs", self.HIGHLIGHT_HRS) or 0)
    highlight_mins = int (form.get ("highlight_mins", self.HIGHLIGHT_MINS) or 0)
    highlight_delta = datetime.timedelta (days=highlight_days, hours=highlight_hrs, minutes=highlight_mins)
    highlight_deltastamp = deltastamp (highlight_delta)
    if files:
      title = cgi.escape ("Top %d files on %s over %dMb - %s" % (min (len (files), self.TOP_N_FILES), path, size_threshold_mb, status))
    else:
      title = cgi.escape ("Top files on %s over %dMb - %s" % (path, size_threshold_mb, status))

    doc = []
    doc.append (u"<html><head><title>%s</title>" % title)
    doc.append (u"""<style>
    body {font-family : calibri, verdana, sans-serif;}
    h1 {font-size : 120%;}
    form#params {font-size : 120%;}
    form#params input {font-family : calibri, verdana, sans-serif;}
    form#params span.label {font-weight : bold;}
    p.updated {margin-bottom : 1em; font-style : italic;}
    table {width : 100%;}
    thead tr {background-color : black; color : white; font-weight : bold;}
    table tr.odd {background-color : #ddd;}
    table tr.highlight td {background-color : #ffff80;}
    table td {padding-right : 0.5em;}
    table td.filename {width : 72%;}
    </style>""")
    doc.append (u"""<style media="print">
    form#params {display : none;}
    </style>""")
    doc.append (u"</head><body>")
    doc.append (u"""<form id="params" action="/" method="GET">
    <span class="label">Scan</span>&nbsp;<input type="text" name="path" value="%(path)s" size="20" maxlength="20" />&nbsp;
    <span class="label">for files over</span>&nbsp;<input type="text" name="size_threshold_mb" value="%(size_threshold_mb)s" size="5" maxlength="5" />Mb
    <span class="label">showing the top</span>&nbsp;<input type="text" name="top_n_files" value="%(top_n_files)s" size="3" maxlength="3" /> files
    <span class="label">refreshing every</span>&nbsp;<input type="text" name="refresh_secs" value="%(refresh_secs)s" size="3" maxlength="3" /> secs
    <span class="label">highlighting the last&nbsp;</span>&nbsp;<input type="text" name="highlight_days" value="%(highlight_days)s" size="3" maxlength="3" /> days
      </span>&nbsp;<input type="text" name="highlight_hrs" value="%(highlight_hrs)s" size="3" maxlength="3" /> hrs
      </span>&nbsp;<input type="text" name="highlight_mins" value="%(highlight_mins)s" size="3" maxlength="3" /> mins
    <input type="submit" value="Refresh" />
    </form><hr>""" % locals ())

    now = win32timezone.utcnow ()
    if path:
      doc.append (u"<h1>%s</h1>" % title)
      latest_filename = "\\".join (files[-1].parts[1:]) if files else "(no file yet)"
      doc.append (u'<p class="updated">Last updated %s</p>' % time.asctime ())
      doc.append (u'<table><thead><tr><td class="filename">Filename</td><td class="size">Size (Mb)</td><td class="updated">Updated</td></tr></thead>')
      for i, f in enumerate (files[:top_n_files]):
        try:
          doc.append (
            u'<tr class="%s %s"><td class="filename">%s</td><td class="size">%5.2f</td><td class="updated">%s</td>' % (
              "odd" if i % 2 else "even",
              "highlight" if ((now - max (f.written_at, f.created_at)) <= highlight_delta) else "",
              f.relative_to (path).lstrip (fs.seps),
              f.size / 1024.0 / 1024.0,
              max (f.written_at, f.created_at)
            )
          )
        except fs.exc.x_winsys:
          pass
      doc.append (u"</table>")

    doc.append (u"</body></html>")
    return doc

  def handler (self, form):
    path = form.get ("path", self.PATH)
    size_threshold_mb = int (form.get ("size_threshold_mb", self.SIZE_THRESHOLD_MB) or 0)
    refresh_secs = int (form.get ("refresh_secs", self.REFRESH_SECS) or 0)
    status = "Waiting"
    if path and fs.Dir (path):
      #
      # Ignore any non-existent paths, including garbage.
      # Create a new path handler if needed, or pull back
      # and existing one, and return the latest list.
      #
      with self._paths_lock:
        if path not in self.paths:
          self.paths[path] = Path (path, size_threshold_mb, self.N_FILES_AT_A_TIME)
        path_handler = self.paths[path]
        if path_handler._size_threshold_mb != size_threshold_mb:
          path_handler.finish ()
          path_handler = self.paths[path] = Path (path, size_threshold_mb, self.N_FILES_AT_A_TIME)
        self._paths_accessed[path] = win32timezone.utcnow ()
        files = sorted (path_handler.updated (), key=operator.attrgetter ("size"), reverse=True)
        status = path_handler.status ()

        #
        # If any path hasn't been queried for at least
        # three minutes, close the thread down and delete
        # its entry. If it is queried again, it will just
        # be restarted as new.
        #
        for path, last_accessed in self._paths_accessed.items ():
          if (win32timezone.utcnow () - last_accessed).seconds > 180:
            path_handler = self.paths.get (path)
            if path_handler:
              path_handler.finish ()
              del self.paths[path]
              del self._paths_accessed[path]

    else:
      files = []
    return self.doc (files, status, form)

  def __call__ (self, environ, start_response):
    """Only attempt to handle the root URI. If a refresh interval
    is requested (the default) then send a header which forces
    the refresh.
    """
    path = shift_path_info (environ).rstrip ("/")
    if path == "":
      form = dict ((k, v[0]) for (k, v) in cgi.parse_qs (environ['QUERY_STRING']).items () if v)
      if form.get ("path"):
        form['path'] = form['path'].rstrip ("\\") + "\\"
      refresh_secs = int (form.get ("refresh_secs", self.REFRESH_SECS) or 0)
      headers = []
      headers.append (("Content-Type", "text/html; charset=utf-8"))
      if refresh_secs:
        headers.append (("Refresh", "%s" % refresh_secs))
      start_response ("200 OK", headers)
      return (d.encode ("utf8") + "\n" for d in self.handler (form))
    else:
      start_response ("404 Not Found", [("Content-Type", "text/plain")])
      return []

  def finish (self):
    for path_handler in self.paths.values ():
      path_handler.finish ()

if __name__ == '__main__':
  misc.set_console_title ("Monitor Directory")
  PORT = 8000
  HOSTNAME = socket.getfqdn ()
  threading.Timer (
    2.0,
    lambda: os.startfile ("http://%s:%s" % (HOSTNAME, PORT))
  ).start ()

  app = App ()
  try:
    make_server ('', PORT, app).serve_forever ()
  except KeyboardInterrupt:
    print "Shutting down gracefully..."
  finally:
    app.finish ()
