# -*- coding: iso-8859-1 -*-
u"""Provide unified access to the different sets of constants used by
the winsys module. Some of them are provided by modules within the
pywin32 package. Others belong to those sets but are not present in
the modules. Still others are not present at all within pywin32 and
are added here manually.

The constants are grouped together into :class:`Constants` classes
which combine the effect of being a namespace and also providing
functions to list the constant name or names given a value, which
is useful when displaying Win32 structures.

For useful documentation, each :class:`Constants` generates a readable
docstring tabulating its names & values.
"""
import operator
import re

import win32con
import win32event
import ntsecuritycon
import fnmatch

from winsys import utils

def from_pattern (pattern, name):
  ur"""Helper function to find the common pattern among a group
  of like-named constants. eg if the pattern is FILE_ACCESS_*
  then the part of the name after FILE_ACCESS_ will be returned.
  """
  if pattern is None:
    return name
  else:
    return re.search (pattern.replace ("*", r"(\w+)"), name).group (1)

class Constants (object):
  ur"""Provide a dict-like interface for a group of related
  constants. These can come from a module or other namespace according
  to a wildcard name, or can be added as a list of (unrelated) names from 
  a namespace or can simply be a raw dictionary of name-value pairs::
  
    import win32con
    from winsys import constants
    COMPRESSION_ENGINE = constants.Constants.from_pattern (
      "COMPRESSION_ENGINE_*", 
      namespace=win32con
    )
    COMPRESSION_ENGINE.update (dict (
      EXTRA_VALUE = 5
    ))
    print COMPRESSION_ENGINE.MAXIMUM
    print COMPRESSION_ENGINE.__doc__
    
  The convention is to name the set of constants after the common
  prefix of the constant names, as in the example above, but it's
  just a convention. The pattern parameter to the various factory
  functions will be used to rename the constants on the way in,
  but it can be empty.
  
  The constants can be accessed as attributes or as items. In addition,
  passing a name or a value to the :meth:`constant` method will return
  the value.
  
  To retrieve the name or names corresponding to a value, use the
  :meth:`name_from_value` or :meth:`names_from_value` function::
  
    import win32con
    from winsys import constants
    ACE_TYPES = constants.Constants.from_pattern (
      "*_ACE_TYPE",
      namespace=win32con
    )
    print ACE_TYPES.name_from_value (ACE_TYPES.ACCESS_ALLOWED)
  """
  
  def __init__ (self, dict_initialiser):
    u"""Build an internal structure from a dictionary-like
    set of initial values.
    """
    self._dict = dict (dict_initialiser)
    self.preamble = ""
    self.reset_doc ()

  def __getitem__ (self, attribute):
    u"""Act as a dictionary and as a namespace so that calls like 
    FILE_ACCESS["READ"] and FILE_ACCESS.READ will both succeed.
    """
    return self._dict[attribute]
  
  def __getattr__ (self, attribute):
    try:
      return self._dict[attribute]
    except KeyError:
      raise AttributeError
  
  def __repr__ (self):
    return "<Constants: %r>" % self._dict
    
  def __str__ (self):
    return "<Constants: %s>" % ", ".join (self._dict.keys ())
    
  def reset_doc (self):
    namelen = len (max (self._dict, key=len))
    try:
      int (self._dict.values ()[0])
    except:
      valuelen = len (max (self._dict.values (), key=len))
      prefix = ""
      row_format = "|%%-%ds|%%-%ds|" % (namelen, valuelen)
      converter = unicode
    else:
      valuelen = 2 * ((1 + len ("%x" % max (self._dict.values ()))) // 2)
      prefix = "0x"
      row_format = "|%%-%ds|%s%%0%dX|" % (namelen, prefix, valuelen)
      converter = utils.signed_to_unsigned 
      
    separator = "+" + namelen * "-" + "+" + (len (prefix) + valuelen) * "-" + "+"
    row = separator + "\n" + row_format
    table = "\n".join (row % (k, converter (v)) for (k, v) in sorted (self._dict.items (), key=operator.itemgetter (1))) + "\n" + separator
    self.__doc__ = self.preamble + "\n\n" + table
  
  def doc (self, preamble):
    self.preamble = preamble
    self.reset_doc ()

  def dump (self):
    print self.__doc__
  
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
    self.reset_doc ()
    
  def items (self):
    return self._dict.items ()
    
  def keys (self):
    return self._dict.keys ()

  def __iter__ (self):
    return iter (self._dict)
    
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
  def from_list (cls, keys, namespace, pattern=None):
    u"""Factory method to return a class instance from a list-like set of values
    within a namespace. Hands off to the from_dict factory.
    """
    return cls ((from_pattern (pattern, key), getattr (namespace, key, None)) for key in keys)

  @classmethod
  def from_pattern (cls, pattern=u"*", excluded=[], namespace=win32con):
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

GENERAL = Constants.from_dict (dict (
  MAXIMUM_ALLOWED=ntsecuritycon.MAXIMUM_ALLOWED,
  INFINITE=win32event.INFINITE
))
TOKEN_FLAG = Constants.from_pattern (u"TOKEN_*")

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
