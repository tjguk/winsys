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
