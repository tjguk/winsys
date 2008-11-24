# -*- coding: iso-8859-1 -*-
import os, sys
import contextlib
import operator

import win32security
import win32api
import pywintypes
import winerror

from winsys import core, utils
from winsys.constants import *
from winsys.exceptions import *

PyHANDLE = pywintypes.HANDLEType
PyACL = pywintypes.ACLType
PySECURITY_ATTRIBUTES = pywintypes.SECURITY_ATTRIBUTESType

class x_privilege (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_privilege)

class Privilege (core._WinSysObject):

  def __init__ (self, luid, attributes=0):
    u"""luid is one of the PRIVILEGE_NAME constants
    attributes is the result of or-ing the different PRIVILEGE_ATTRIBUTE items you want
    """
    core._WinSysObject.__init__ (self)
    self._luid = luid
    self._attributes = attributes
    self.name = wrapped (win32security.LookupPrivilegeName, u"", self._luid)
    self.description = wrapped (win32security.LookupPrivilegeDisplayName, u"", self.name)
    
  def as_string (self):
    attributes = self._attributes
    if attributes == 0:
      prefix = u"-"
    elif PRIVILEGE_ATTRIBUTE.ENABLED_BY_DEFAULT & attributes:
      prefix = u"*"
    elif PRIVILEGE_ATTRIBUTE.ENABLED & attributes:
      prefix = u"+"
    else:
      prefix = u" "
    return u"%s %s (%d)" % (prefix, self.name, self._luid)
  
  def dumped (self, level=0):
    output = []
    output.append (u"Name: %s" % self.name)
    output.append (u"LUID: %s" % self._luid)
    output.append (u"Attributes: %s" % u" | " .join (PRIVILEGE_ATTRIBUTE.names_from_value (self._attributes)))
    return utils.dumped (u"\n".join (output), level)

  def __eq__ (self, other):
    return self.name == other.name
    
  def __lt__ (self, other):
    return self.name < other.name
    
  def pyobject (self):
    return self._luid
    
  def _get_enabled (self):
    return bool (self._attributes & PRIVILEGE_ATTRIBUTE.ENABLED)
  enabled = property (_get_enabled)

  @classmethod
  def from_string (cls, string):
    return cls (wrapped (win32security.LookupPrivilegeValue, u"", unicode (string)))
  
def privilege (privilege):
  u"""Friendly constructor for the Privilege class"""
  if issubclass (privilege.__class__, Privilege):
    return privilege
  elif issubclass (privilege.__class__, int):
    return Privilege (privilege)
  else:
    return Privilege.from_string (unicode (privilege))
