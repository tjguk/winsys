# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os
from datetime import datetime, timedelta
import re
import struct
import threading
import pywintypes
import winxpgui as win32gui

#
# Small support functions
#
def from_pytime (pytime):
  try:
    return datetime.fromtimestamp (int (pytime))
  except ValueError:
    return None

def signed_to_unsigned (signed):
  """Convert a (possibly signed) long to unsigned hex"""
  unsigned, = struct.unpack ("L", struct.pack ("l", signed))
  return unsigned

def mask_as_string (mask, length=32):
  return "".join (u"01"[bool (mask & (1 << i))] for i in range (length)[::-1])

def mask_as_list (mask, length=32):
  return [i for i in range (length) if ((1 << i) & mask)]

def _longword (lo, hi):
  return lo + (hi * 1 << 32)

def _set (obj, attr, value):
  obj.__dict__[attr] = value

def secs_as_string (secs):
  """Convert a number of seconds to dh'", eg

  25 => 25"
  190 => 3'10"
  6800 => 1h53'20"
  440000 => 5d2h13'20"
  345600 => 4d
  """
  d = timedelta (seconds=secs)
  days = d.days
  minutes, seconds = divmod (d.seconds, 60)
  hours, minutes = divmod (minutes, 60)
  return "".join ([
    "%dd" % days if days else "",
    "%dh" % hours if hours else "",
    "%d'" % minutes if minutes else "",
    '%d"' % seconds if seconds else ""
  ])

def size_as_mb (n_bytes):
  """Convert a size in bytes to a human-readable form as follows:

  If < kb return the number unchanged
  If >= kb and < mb return number of kb
  If >= mb and < gb return number of mb
  Otherwise return number of gb
  """
  n_kb, n_b = divmod (n_bytes, 1024)
  n_mb, n_kb = divmod (n_kb, 1024)
  n_gb, n_mb = divmod (n_mb, 1024)
  if n_gb > 0:
    return "%3.2fGb" % (n_bytes / 1024.0 / 1024.0 / 1024.0)
  elif n_mb > 0:
    return "%3.2fMb" % (n_bytes / 1024.0 / 1024.0)
  elif n_kb > 0:
    return "%3.2fkb" % (n_bytes / 1024.0)
  else:
    return "%d" % n_bytes

#
# Support functions for dump functionality.
#
def indented (text, level, indent=2):
  """Take a multiline text and indent it as a block"""
  return u"\n".join (u"%s%s" % (level * indent * u" ", s) for s in text.splitlines ())

def dumped (text, level, indent=2):
  """Put curly brackets round an indented text"""
  return indented (u"{\n%s\n}" % indented (text, level+1, indent) or "None", level, indent)

def dumped_list (l, level, indent=2):
  return dumped (u"\n".join (unicode (i)  for i in l), level, indent)

def dumped_dict (d, level, indent=2):
  return dumped (u"\n".join (u"%s => %s" % (k, v) for (k, v) in d.iteritems ()), level, indent)

def dumped_flags (f, lookups, level, indent=2):
  return dumped (u"\n".join (lookups.names_from_value (f)) or u"None", level, indent)

def pythonised (string):
  """Convert from initial caps to lowercase with underscores.
  eg, given "TimGolden" return "tim_golden"
  """
  return "_".join (s.lower () for s in re.findall (r"([A-Z][a-z]+)", string))

#
# Support functions for translating to/from the WinAPI
#
def string_as_pointer (string):
  """Convert a Python string to a LPSTR for the WinAPI"""
  address, length = win32gui.PyGetBufferAddressAndLen (buffer (string))
  return address

def pointer_as_string (pointer, length=0):
  """Convert a WinAPI LPSTR to a Python string"""
  return win32gui.PyGetString (pointer, length)

def relative_to (path1, path0):
  """Entirely unsophisticated functionality to remove a short
  path from the beginning of a longer one off the same root.
  This is to assist in things like copying a directory or registry
  tree from one area to another.

  NB This is used by the fs *and* registry modules so stays
  here in the global utils
  """
  path1 = unicode (path1).lower ()
  path0 = unicode (path0).lower ()
  if path1.startswith (path0):
    return path1[len (path0):]
  else:
    raise RuntimeError ("%s and %s have nothing in common" % (path1, path0))
