# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os
from datetime import datetime
import re
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

def mask_as_string (mask, length=32):
  return "".join (u"01"[bool (mask & (2 << i))] for i in range (length)[::-1])

def mask_as_list (mask, length=32):
  return [i for i in range (length) if ((2 << i) & mask)]

def _longword (lo, hi):
  return lo + (hi * 2 << 31)

def _set (obj, attr, value):
  obj.__dict__[attr] = value

def relative_to (path1, path0):
  """Entirely unsophisticated functionality to remove a short
  path from the beginning of a longer one off the same root.
  This is to assist in things like copying a directory or registry
  tree from one area to another.
  """
  path1 = normalised (path1).lower ()
  path0 = normalised (path0).lower ()
  if path1.startswith (path0):
    return path1[len (path0):]
  else:
    raise RuntimeError ("%s and %s have nothing in common" % (path1, path0))

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
  #~ return indented (u"{\n%s\n}" % indented (u"\n".join (unicode (i)  for i in l) or u"None", level+1, indent), level, indent)

def dumped_dict (d, level, indent=2):
  return dumped (u"\n".join (u"%s => %s" % (k, v) for (k, v) in d.items ()), level, indent)
  #~ return indented (u"{\n%s\n}" % indented (u"\n".join (u"%s => %s" % (k, v) for (k, v) in d.items ()) or u"None", level+1, indent), level, indent)

def dumped_flags (f, lookups, level, indent=2):
  return dumped (u"\n".join (lookups.names_from_value (f)) or u"None", level, indent)
  #~ return indented (u"{\n%s\n}" % indented (u"\n".join (lookups.names_from_value (f)) or u"None", level+1, indent), level, indent)

def pythonised (string):
  """Convert from initial caps to lowercase with underscores"""
  return "_".join (s.lower () for s in re.findall (r"([A-Z][a-z]+)", string))

#
# Support functions for translating to/from the WinAPI
#
def string_as_pointer (string):
  """Convert a Python string to a LPSTR for the WinAPI"""
  address, length = win32gui.PyGetBufferAddressAndLen (buffer (string))
  return address
  
def pointer_as_string (pointer):
  """Convert a WinAPI LPSTR to a Python string"""
  return win32gui.PyGetString (pointer)
