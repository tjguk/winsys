# -*- coding: iso-8859-1 -*-
u"""Functions & classes to support working with security
principals: users, groups, sids &c.
"""
from __future__ import with_statement
import os, sys

import win32security
import win32api
import pywintypes
import winerror

from winsys import core, utils
from winsys.exceptions import *
from constants import *

PySID = pywintypes.SIDType

class x_security (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_security)

def principal (principal):
  u"""Factory function for the Principal class. principal
  parameter can be:
  
  None - return None
  Principal - return itself
  PySID - return the corresponding Principal
  account name - return the corresponding Principal
  """
  if principal is None:
    return None
  elif type (principal) == PySID:
    return Principal (principal)
  elif issubclass (principal.__class__, Principal):
    return principal
  else:
    return Principal.from_string (unicode (principal))

class Principal (core._WinSysObject):
  u"""Object wrapping a Windows security principal, represented by a SID
  and, where possible, a name.
  """

  type = None
  
  def __init__ (self, sid, system_name=None):
    u"""Initialise a Principal from and (optionally) a system name. The sid
    must be a PySID and the system name, if present must be a security
    authority.
    """
    core._WinSysObject.__init__ (self)
    self.sid = sid
    try:
      self.name, self.domain, self.type = wrapped (win32security.LookupAccountSid, system_name, self.sid)
    except x_winsys, (errmsg, errctx, errno):
      if errno == winerror.ERROR_NONE_MAPPED:
        self.name = str (self.sid)
        self.domain = self.type = None
      else:
        raise

  def __hash__ (self):
    return hash (self.sid)
  
  def __eq__ (self, other):
    return self.sid == principal (other).sid
    
  def __lt__ (self, other):
    return self.sid < principal (other).sid

  def pyobject (self):
    return self.sid

  def as_string (self):
    if self.domain:
      return ur"%s\%s" % (self.domain, self.name)
    else:
      return self.name or str (self.sid)

  def dumped (self, level):
    return utils.dumped (u"user: %s\nsid: %s" % (
      self.as_string (), 
      wrapped (win32security.ConvertSidToStringSid, self.sid)
    ), level)

  def logon (self, password):
    u"""Log on as an authenticated user, returning that
    user's token. This is used by security.impersonate
    which wraps the token in a Token object and manages
    its lifetime in a context.
    """
    hUser = wrapped (
      win32security.LogonUser,
      self.name,
      self.domain,
      password,
      LOGON.LOGON_NETWORK,
      LOGON.PROVIDER_DEFAULT
    )
    return hUser

  @classmethod
  def from_string (cls, string, system_name=None):
    u"""string is the name of an account in the form "domain\name".
    The domain is optional, so the simplest form is simply "name"
    """
    if string == "":
      string = win32api.GetUserNameEx (win32con.NameSamCompatible)
    sid, domain, type = wrapped (
      win32security.LookupAccountName,
      None if system_name is None else unicode (system_name), 
      unicode (string)
    )
    return cls (sid, None if system_name is None else unicode (system_name))

  @classmethod
  def from_well_known (cls, well_known, domain):
    return cls (wrapped (win32security.CreateWellKnownSid, well_known, principal (domain)))

  @classmethod
  def me (cls):
    u"""Convenience factory method for the common case of referring to the 
    logged-on user
    """
    return cls.from_string (wrapped (win32api.GetUserNameEx, EXTENDED_NAME.SamCompatible))

class User (Principal):
  pass
  
class Group (Principal):
  pass

#
# Module-level convenience functions
#
def me ():
  return Principal.me ()
