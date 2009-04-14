# -*- coding: iso-8859-1 -*-
u"""Functions & classes to support working with security
principals: users, groups, sids &c.
"""
from __future__ import with_statement
import os, sys
import contextlib
import socket

import win32con
import win32security
import win32api
import win32cred
import pywintypes
import winerror

from . import constants, core, utils
from .exceptions import (
  wrapper, x_winsys, x_not_found
)

__all__ = ['LOGON', 'EXTENDED_NAME', 'x_accounts', 'principal', 'Principal', 'User', 'Group', 'me']

LOGON = constants.Constants.from_pattern (u"LOGON32_*", namespace=win32security)
EXTENDED_NAME = constants.Constants.from_pattern (u"Name*", namespace=win32con)
CREDUI_FLAGS = constants.Constants.from_pattern (u"CREDUI_FLAGS_*", namespace=win32cred)
CRED_FLAGS = constants.Constants.from_pattern (u"CRED_FLAGS_*", namespace=win32cred)
CRED_TYPE = constants.Constants.from_pattern (u"CRED_TYPE_*", namespace=win32cred)
CRED_TI = constants.Constants.from_pattern (u"CRED_TI_*", namespace=win32cred)

PySID = pywintypes.SIDType

class x_accounts (x_winsys):
  pass

WINERROR_MAP = {
  winerror.ERROR_NONE_MAPPED : x_not_found
}
wrapped = wrapper (WINERROR_MAP, x_accounts)

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
  elif isinstance (principal, Principal):
    return principal
  else:
    return Principal.from_string (unicode (principal))

class Principal (core._WinSysObject):
  u"""Object wrapping a Windows security principal, represented by a SID
  and, where possible, a name.
  """

  def __init__ (self, sid, system_name=None):
    u"""Initialise a Principal from and (optionally) a system name. The sid
    must be a PySID and the system name, if present must be a security
    authority.
    """
    core._WinSysObject.__init__ (self)
    self.sid = sid
    try:
      self.name, self.domain, self.type = wrapped (win32security.LookupAccountSid, system_name, self.sid)
    except x_winsys, (errno, errctx, errmsg):
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

  def logon (self, password=core.UNSET, logon_type=core.UNSET):
    u"""Log on as an authenticated user, returning that
    user's token. This is used by security.impersonate
    which wraps the token in a Token object and manages
    its lifetime in a context.
    """
    if logon_type is core.UNSET:
      logon_type = LOGON.LOGON_NETWORK
    if password is core.UNSET:
      flags = 0
      flags |= CREDUI_FLAGS.GENERIC_CREDENTIALS
      flags |= CREDUI_FLAGS.DO_NOT_PERSIST
      _, password, _ = wrapped (
        win32cred.CredUIPromptForCredentials,
        self.domain, 
        0, 
        self.name, 
        None,
        False, 
        flags, 
        {}
      )
    hUser = wrapped (
      win32security.LogonUser,
      self.name,
      self.domain,
      password,
      logon_type,
      LOGON.PROVIDER_DEFAULT
    )
    return hUser

  @classmethod
  def from_string (cls, string, system_name=None):
    u"""string is the name of an account in the form "domain\name".
    The domain is optional, so the simplest form is simply "name"
    """
    if string == "":
      string = wrapped (win32api.GetUserNameEx, win32con.NameSamCompatible)
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
    
  @contextlib.contextmanager
  def impersonate (self, password=core.UNSET, logon_type=core.UNSET):
    hLogon = self.logon (password, logon_type)
    wrapped (win32security.ImpersonateLoggedOnUser, hLogon)
    yield hLogon
    wrapped (win32security.RevertToSelf)
    
  def __enter__ (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.logon (logon_type=LOGON.LOGON_INTERACTIVE))
  
  def __exit__ (self, exc_type, exc_val, exc_tb):
    wrapped (win32security.RevertToSelf)

class User (Principal): pass
  
class Group (Principal): pass

#
# Module-level convenience functions
#
def me ():
  return Principal.me ()
