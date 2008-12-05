# -*- coding: iso-8859-1 -*-
import os, sys

import winerror
import win32api
import win32security

from winsys import constants, core, utils
from winsys.exceptions import *

PRIVILEGE_ATTRIBUTE = constants.Constants.from_pattern (u"SE_PRIVILEGE_*", namespace=win32security)
PRIVILEGE = constants.Constants.from_pattern (u"SE_*_NAME", namespace=win32security)

class x_privilege (x_winsys):
  pass
  
class x_privilege_no_token (x_privilege):
  pass

WINERROR_MAP = {
  winerror.ERROR_NO_TOKEN : x_privilege_no_token
}
wrapped = wrapper (WINERROR_MAP, x_privilege)

#
# Convenience implementation functions
#
def _get_token ():
  try:
    return wrapped (
      win32security.OpenThreadToken, 
      wrapped (win32api.GetCurrentThread), 
      constants.MAXIMUM_ALLOWED, 
      True
    )
  except x_privilege_no_token:
    return wrapped (
      win32security.OpenProcessToken, 
      wrapped (win32api.GetCurrentProcess),
      constants.MAXIMUM_ALLOWED
    )
  
def _set_privilege (self, luid, enable=True):
  wrapped (
    win32security.AdjustTokenPrivileges, 
    _get_token (), 
    False, 
    [(luid, PRIVILEGE_ATTRIBUTE.ENABLED if enable else 0)]
  )

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
  def _set_enabled (self, set):
    raise NotImplemented
    _set_privilege (self._luid, set)
    if set:
      self._attributes |= PRIVILEGE_ATTRIBUTE.ENABLED
    else:
      self._attributes &= ~PRIVILEGE_ATTRIBUTE.ENABLED
  enabled = property (_get_enabled, _set_enabled)

  @classmethod
  def from_string (cls, string):
    return cls (wrapped (win32security.LookupPrivilegeValue, u"", unicode (string)))
  
def privilege (privilege):
  u"""Friendly constructor for the Privilege class"""
  if isinstance (privilege, Privilege):
    return privilege
  elif isinstance (privilege, int):
    return Privilege (privilege)
  elif isinstance (privilege, tuple):
    return Privilege (*privilege)
  else:
    return Privilege.from_string (unicode (privilege))

