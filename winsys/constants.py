# -*- coding: iso-8859-1 -*-
"""Provide unified access to the different sets of constants used by
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

from winsys import core, utils

def from_pattern (pattern, name):
  r"""Helper function to find the common pattern among a group
  of like-named constants. eg if the pattern is FILE_ACCESS_*
  then the part of the name after FILE_ACCESS_ will be returned.
  """
  if pattern is None:
    return name
  else:
    return re.search (pattern.replace ("*", r"(\w+)"), name).group (1)

class Constants (core._WinSysObject):
  r"""Provide a dict-like interface for a group of related
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
    COMPRESSION_ENGINE.dump ()

  The convention is to name the set of constants after the common
  prefix of the constant names, as in the example above, but it's
  just a convention. The pattern parameter to the various factory
  functions will be used to rename the constants on the way in,
  but it can be empty.

  The constants can be accessed as attributes or as items. In addition,
  passing a name or a value to the :meth:`constant` method will return
  the value. This is done automatically by most functions which expect
  a parameter based on one of these constants sets.

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

  def __init__ (self, dict_initialiser={}):
    """Build an internal structure from a dictionary-like
    set of initial values.
    """
    self.preamble = ""
    self._dict = {}
    self._key_dict = {}
    self.init (dict_initialiser)

  def __getitem__ (self, attribute):
    """Act as a dictionary and as a namespace so that calls like
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

  def init (self, dict_initialiser):
    items = list (dict_initialiser)
    self._dict.update ((name, value) for key, name, value in items)
    self._key_dict.update ((value, key) for key, name, value in items)
    self.reset_doc ()

  def reset_doc (self):
    if not self._dict:
      self.__doc__ = ""
      return

    namelen = len (max (self._dict, key=len))
    aliaslen = len (max (self._key_dict.values (), key=len))
    try:
      int (self._dict.values ()[0])
    except:
      valuelen = len (max ((str (v) for v in self._dict.values ()), key=len))
      prefix = ""
      row_format = "|%%-%ds|%%-%ds|%%-%ds|" % (namelen, valuelen, aliaslen)
      converter = str
    else:
      valuelen = 2 * ((1 + len ("%x" % max (self._dict.values ()))) // 2)
      prefix = "0x"
      row_format = "|%%-%ds|%s%%0%dX|%%-%ds|" % (namelen, prefix, valuelen, aliaslen)
      converter = utils.signed_to_unsigned
    header_format = "|%%-%ds|%%-%ds|%%-%ds|" % (namelen, len (prefix) + valuelen, aliaslen)

    separator = "+" + namelen * "-" + "+" + (len (prefix) + valuelen) * "-" + "+" + aliaslen * "-" + "+"
    header = "+" + namelen * "=" + "+" + (len (prefix) + valuelen) * "=" + "+" + aliaslen * "=" + "+"
    row = row_format + "\n" + separator
    rows = ((name, converter (value), self._key_dict[value]) for (name, value) in self._dict.items ())
    table = "\n".join ([
      separator,
      header_format % ("Name", "Val", "Win32"),
      header,
      "\n".join (row % r for r in sorted (rows, key=operator.itemgetter (1))),
    ])
    self.__doc__ = self.preamble + "\n\n" + table

  def doc (self, preamble):
    self.preamble = preamble
    self.reset_doc ()

  def dumped (self, level=None):
    return self.__doc__

  def __contains__ (self, attribute):
    return attribute in self._dict

  def constant (self, value):
    """From a value, which may be a string or an integer, determine
    the corresponding value in this set of constants. If the value
    is a number, it is passed straight back out. If not, it is
    assumed to be a single string or a list of strings, each string
    corresponding to one of the constants in this set of constants::

      from winsys.security import SD_CONTROL

      print SD_CONTROL.constant (["dacl_protected", "sacl_protected"])
      print SD_CONTROL.DACL_PROTECTED | SD_CONTROL.SACL_PROTECTED
      print SD_CONTROL.constant (12288)

    ..  note::
        No attempt is made to verify that the number passed in represents
        a combination of the constants in this set.
    """
    if value is None:
      return None
    elif isinstance (value, list):
      return reduce (operator.or_, (self[str (v.strip ().upper ())] for v in value))
    elif value in self._key_dict:
      return value
    elif isinstance (value, int):
      return value
    elif isinstance (value, str):
      if value in self._dict:
        return self._dict[value]
      else:
        return self[value.strip ().upper ()]

  def update (self, other):
    """Act as a dict for updates so that several constant sets may
    be merged into one.
    """
    self.init ((key, key, value) for key, value in other.items ())

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
    """Factory method to return a class instance from a dictionary-like set of values.
    If a pattern is passed in, use the distinguished part of the name (the part
    which matches the wildcard) as the key name.
    """
    return cls ((key, from_pattern (pattern, key), value) for (key, value) in d.items ())

  @classmethod
  def from_list (cls, keys, namespace, pattern=None):
    """Factory method to return a class instance from a list-like set of values
    within a namespace. Hands off to the from_dict factory.
    """
    return cls ((key, from_pattern (pattern, key), getattr (namespace, key, None)) for key in keys)

  @classmethod
  def from_pattern (cls, pattern="*", excluded=[], namespace=win32con):
    """Factory method to return a class instance from a wildcard name pattern. This is
    the most common method of constructing a list of constants by passing in, eg,
    FILE_ATTRIBUTE_* and the win32file module as the namespace.
    """
    return cls (
      (key, from_pattern (pattern, key), getattr (namespace, key)) for \
        key in dir (namespace) if \
        fnmatch.fnmatch (key, pattern) and \
        key not in excluded
    )

  def names (self, patterns=["*"]):
    """From a list of patterns, return the matching names from the
    list of constants. A single string is considered as though a
    list of one.
    """
    if isinstance (patterns, str):
      patterns = [patterns]
    for name in self._dict.keys ():
      for pattern in patterns:
        if fnmatch.fnmatch (name, pattern):
          yield name

  def names_from_value (self, value, patterns=["*"]):
    """From a number representing the or-ing of several integer values,
    work out which of the constants make up the number using the pattern
    to filter the "classes" or constants present in the dataset.
    """
    return [name for name in self.names (patterns) if value & self[name]]

  def name_from_value (self, value, default=core.UNSET, patterns=["*"]):
    """Find the one name in the set of constants (optionally qualified by pattern)
    which matches value.
    """
    for name in self.names (patterns):
      if self[name] == value:
        return name
    else:
      if default is core.UNSET:
        raise KeyError ("No constant matching name %s and value %s" % (patterns, value))
      else:
        return default

  def values_from_value (self, value, patterns=["*"]):
    """Return the list of values which make up the combined value
    """
    return [self._dict[name] for name in names_from_value (value, patterns)]

GENERAL = Constants.from_dict (dict (
  MAXIMUM_ALLOWED=ntsecuritycon.MAXIMUM_ALLOWED,
  INFINITE=win32event.INFINITE
))
TOKEN_FLAG = Constants.from_pattern ("TOKEN_*")

ACCESS = Constants.from_list ([
  "DELETE",
  "READ_CONTROL",
  "WRITE_DAC",
  "WRITE_OWNER",
  "SYNCHRONIZE"
], namespace=ntsecuritycon)
ACCESS.update (dict (
  ACCESS_SYSTEM_SECURITY = win32con.ACCESS_SYSTEM_SECURITY
))
GENERIC_ACCESS = Constants.from_pattern ("GENERIC_*", namespace=ntsecuritycon)
STANDARD_ACCESS = Constants.from_list (["STANDARD_RIGHTS_READ", "STANDARD_RIGHTS_WRITE", "SYNCHRONIZE"], namespace=ntsecuritycon)

#~ SCHEDULED_TASK_ERROR = Constants.from_pattern ("SCHED_E_*", namespace=taskscheduler)
#~ TASKPAGE = Constants.from_pattern ("TASKPAGE_*", namespace=taskscheduler)
#~ TASK = Constants.from_pattern ("TASK_*", namespace=taskscheduler)
#~ TASK_PRIORITY = Constants.from_pattern ("*_PRIORITY_CLASS", namespace=taskscheduler)
