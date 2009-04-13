# -*- coding: iso-8859-1 -*-
u"""Provide unified access to the different sets of constants used by
the winsys module. Some of them are provided by modules within the
pywin32 package. Others belong to those sets but are not present in
the modules. Still others are not present at all within pywin32 and
are added here manually.

The constants are grouped together into named Constants classes
which combine the effect of being a namespace and also providing
functions to list the constant name or names given a value, which
is useful when displaying Win32 structures.
"""
import re

#~ from win32com.taskscheduler import taskscheduler
from win32com.shell import shellcon
import win32con
import win32event
import win32evtlog
import win32file
import winioctlcon
import win32security
import ntsecuritycon
import fnmatch

def from_pattern (pattern, name):
  u"""Helper function to find the common pattern among a group
  of like-named constants. eg if the pattern is FILE_ACCESS_*
  then the part of the name after FILE_ACCESS_ will be returned.
  """
  if pattern is None:
    return name
  else:
    return re.search (pattern.replace ("*", r"(\w+)"), name).group (1)

class Constants (object):
  u"""Provide a dict-like interface for a group of related
  constants. These can come from a module or other namespace according
  to a wildcard name, or can be added as a list of (unrelated) names from 
  a namespace or can simply be a raw dictionary of name-value pairs.
  """
  
  def __init__ (self, dict_initialiser):
    u"""Build an internal structure from a dictionary-like
    set of initial values.
    """
    self._dict = dict (dict_initialiser)

  def __getitem__ (self, attribute):
    u"""Act as a dictionary and as a namespace so that calls like 
    FILE_ACCESS["READ"] and FILE_ACCESS.READ will both succeed.
    """
    return self._dict[attribute]
  __getattr__ = __getitem__
  
  def __repr__ (self):
    return "<Constants: %r>" % self._dict
    
  def __str__ (self):
    return "<Constants: %s>" % ", ".join (self._dict.keys ())
    
  def __contains__ (self, attribute):
    return attribute in self.keys ()
  
  def constant (self, value):
    try:
      return int (value)
    except ValueError:
      return self[unicode (value).upper ()]
  
  def update (self, other):
    u"""Act as a dict for updates so that several constant sets may
    be merged into one.
    """
    self._dict.update (dict (other.items ()))
    
  def items (self):
    return self._dict.items ()
    
  def keys (self):
    return self._dict.keys ()
    
  def values (self):
    return self._dict.values ()
  
  @classmethod
  def from_dict (cls, d, pattern=None):
    u"""Factory method to return a class instance from a dictionary-like set of values.
    If a pattern is passed in, use the distinguished part of the name (the part
    which matches the wildcard) as the key name.
    """
    return cls ((from_pattern (pattern, key), value) for (key, value) in d.items ())
  
  @classmethod
  def from_list (cls, keys, namespace=win32security, pattern=None):
    u"""Factory method to return a class instance from a list-like set of values
    within a namespace. Hands off to the from_dict factory.
    """
    return cls ((from_pattern (pattern, key), getattr (namespace, key, None)) for key in keys)

  @classmethod
  def from_pattern (cls, pattern=u"*", excluded=[], namespace=win32security):
    u"""Factory method to return a class instance from a wildcard name pattern. This is
    the most common method of constructing a list of constants by passing in, eg,
    FILE_ATTRIBUTE_* and the win32file module as the namespace.
    """
    return cls (
      (from_pattern (pattern, key), getattr (namespace, key)) for \
        key in dir (namespace) if \
        fnmatch.fnmatch (key, pattern) and \
        key not in excluded
    )
    
  def names (self, patterns=[u"*"]):    
    u"""From a list of patterns, return the matching names from the
    list of constants. A single string is considered as though a
    list of one.
    """
    if isinstance (patterns, basestring):
      patterns = [patterns]
    for name in self._dict.keys ():
      for pattern in patterns:
        if fnmatch.fnmatch (name, pattern):
          yield name
  
  def names_from_value (self, value, patterns=[u"*"]):
    u"""From a number representing the or-ing of several integer values,
    work out which of the constants make up the number using the pattern
    to filter the "classes" or constants present in the dataset.
    """
    return [name for name in self.names (patterns) if value & self[name]]
    
  def name_from_value (self, value, patterns=[u"*"]):
    u"""Find the one name in the set of constants (optionally qualified by pattern)
    which matches value.
    """
    for name in self.names (patterns):
      if self[name] == value:
        return name
    else:
      raise KeyError, u"No constant matching name %s and value %d" % (patterns, value)
      
  def values_from_value (self, value, patterns=["*"]):
    """Return the list of values which make up the combined value
    """
    return [self._dict[name] for name in names_from_value (value, patterns)]

WELL_KNOWN_SID = Constants.from_pattern (u"Win*Sid")
GENERAL = Constants.from_dict (dict (
  MAXIMUM_ALLOWED=ntsecuritycon.MAXIMUM_ALLOWED,
  INFINITE=win32event.INFINITE
))
REVISION = Constants.from_list ([u"ACL_REVISION", u"ACL_REVISION_DS", u"SDDL_REVISION_1"])
TOKEN_FLAG = Constants.from_pattern (u"TOKEN_*")
SID_TYPE = Constants.from_pattern (u"SidType*")

ACCESS = Constants.from_list ([
  u"DELETE",
  u"READ_CONTROL",
  u"WRITE_DAC",
  u"WRITE_OWNER",
  u"SYNCHRONIZE"
], namespace=ntsecuritycon)
ACCESS.update (dict (
  ACCESS_SYSTEM_SECURITY = win32con.ACCESS_SYSTEM_SECURITY
))
GENERIC_ACCESS = Constants.from_pattern (u"GENERIC_*", namespace=ntsecuritycon)
STANDARD_ACCESS = Constants.from_list ([u"STANDARD_RIGHTS_READ", u"STANDARD_RIGHTS_WRITE", u"SYNCHRONIZE"], namespace=ntsecuritycon)

#~ SCHEDULED_TASK_ERROR = Constants.from_pattern (u"SCHED_E_*", namespace=taskscheduler)
#~ TASKPAGE = Constants.from_pattern (u"TASKPAGE_*", namespace=taskscheduler)
#~ TASK = Constants.from_pattern (u"TASK_*", namespace=taskscheduler)
#~ TASK_PRIORITY = Constants.from_pattern (u"*_PRIORITY_CLASS", namespace=taskscheduler)



