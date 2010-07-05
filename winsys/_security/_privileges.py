# -*- coding: iso-8859-1 -*-
import os, sys

import winerror
import win32api
import win32security

from winsys import constants, core, exc, utils

__all__ = ['PRIVILEGE_ATTRIBUTE', 'PRIVILEGE', 'Privilege', 'privilege', 'x_privilege', 'x_privilege_no_token']

PRIVILEGE_ATTRIBUTE = constants.Constants.from_pattern ("SE_PRIVILEGE_*", namespace=win32security)
PRIVILEGE = constants.Constants.from_pattern ("SE_*_NAME", namespace=win32security)
PRIVILEGE.doc ("Privileges granted through a user's token")

class x_privilege (exc.x_winsys):
  "Base for all privilege-related exceptions"

class x_privilege_no_token (x_privilege):
  "Raised when a token cannot be found"

WINERROR_MAP = {
  winerror.ERROR_NO_TOKEN : x_privilege_no_token
}
wrapped = exc.wrapper (WINERROR_MAP, x_privilege)

#
# Convenience implementation functions
#
def _get_token ():
  try:
    return wrapped (
      win32security.OpenThreadToken,
      wrapped (win32api.GetCurrentThread),
      constants.GENERAL.MAXIMUM_ALLOWED,
      True
    )
  except x_privilege_no_token:
    return wrapped (
      win32security.OpenProcessToken,
      wrapped (win32api.GetCurrentProcess),
      constants.GENERAL.MAXIMUM_ALLOWED
    )

def _set_privilege (self, luid, enable=True):
  return wrapped (
    win32security.AdjustTokenPrivileges,
    _get_token (),
    False,
    [(luid, PRIVILEGE_ATTRIBUTE.ENABLED if enable else 0)]
  )

class Privilege (core._WinSysObject):

  def __init__ (self, luid, attributes=0):
    """luid is one of the PRIVILEGE_NAME constants
    attributes is the result of or-ing the different PRIVILEGE_ATTRIBUTE items you want
    """
    core._WinSysObject.__init__ (self)
    self._luid = luid
    self._attributes = attributes
    self.name = wrapped (win32security.LookupPrivilegeName, "", self._luid)
    self.description = wrapped (win32security.LookupPrivilegeDisplayName, "", self.name)

  def as_string (self):
    attributes = self._attributes
    if attributes == 0:
      prefix = "-"
    elif PRIVILEGE_ATTRIBUTE.ENABLED_BY_DEFAULT & attributes:
      prefix = "*"
    elif PRIVILEGE_ATTRIBUTE.ENABLED & attributes:
      prefix = "+"
    else:
      prefix = " "
    return "%s %s (%d)" % (prefix, self.name, self._luid)

  def dumped (self, level=0):
    output = []
    output.append ("Name: %s" % self.name)
    output.append ("LUID: %s" % self._luid)
    output.append ("Attributes: %s" % " | " .join (PRIVILEGE_ATTRIBUTE.names_from_value (self._attributes)))
    return utils.dumped ("\n".join (output), level)

  def __eq__ (self, other):
    return self.name == privilege (other).name

  def __lt__ (self, other):
    return self.name < privilege (other).name

  def pyobject (self):
    return self._luid

  def _get_enabled (self):
    return bool (self._attributes & PRIVILEGE_ATTRIBUTE.ENABLED)
  def _set_enabled (self, set):
    _set_privilege (self._luid, set)
    if set:
      self._attributes |= PRIVILEGE_ATTRIBUTE.ENABLED
    else:
      self._attributes &= ~PRIVILEGE_ATTRIBUTE.ENABLED
  enabled = property (_get_enabled, _set_enabled)

  @classmethod
  def from_string (cls, string):
    return cls (wrapped (win32security.LookupPrivilegeValue, "", str (string)))

  def __enter__ (self):
    self._previous_privs = wrapped (
      win32security.AdjustTokenPrivileges,
      _get_token (),
      False,
      [(self._luid, PRIVILEGE_ATTRIBUTE.ENABLED)]
    )
    return self

  def __exit__ (self, exc_type, exc_val, exc_tb):
    wrapped (
      win32security.AdjustTokenPrivileges,
      _get_token (),
      False,
      self._previous_privs
    )

def privilege (privilege):
  """Friendly constructor for the Privilege class"""
  if isinstance (privilege, Privilege):
    return privilege
  elif isinstance (privilege, int):
    return Privilege (privilege)
  elif isinstance (privilege, tuple):
    return Privilege (*privilege)
  else:
    privilege = str (privilege)
    try:
      return Privilege.from_string (PRIVILEGE.constant (privilege))
    except KeyError:
      return Privilege.from_string (str (privilege))
