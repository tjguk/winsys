# -*- coding: iso-8859-1 -*-
ur"""All security in windows is handled via Security Principals. These can
be a user (the most common case), a group of users, a computer, or something
else. Security principals are uniquely identified by their SID: a binary code
represented by a string S-a-b-cd-efg... where each of the segments represents
an aspect of the security authorities involved. (A computer, a domain etc.).
Certain of the SIDs are considered well-known such as the AuthenticatedUsers
account on each machine which will always have the same SID.

Most of the access to this module will be via the :func:`principal` 
or :func:`me` functions. Although the module is designed to be used
standalone, it is imported directly into the :mod:`security` module's
namespace so its functionality can also be accessed from there.
"""
import os, sys
import contextlib
import socket

import win32con
import win32security
import win32api
import win32cred
import pywintypes
import winerror

from winsys import constants, core, exc, utils

__all__ = ['LOGON', 'EXTENDED_NAME', 'x_accounts', 'principal', 'Principal', 'User', 'Group', 'me']

LOGON = constants.Constants.from_pattern (u"LOGON32_*", namespace=win32security)
LOGON.doc ("Types of logon used by LogonUser and related APIs")
EXTENDED_NAME = constants.Constants.from_pattern (u"Name*", namespace=win32con)
EXTENDED_NAME.doc ("Extended display formats for usernames")
CREDUI_FLAGS = constants.Constants.from_pattern (u"CREDUI_FLAGS_*", namespace=win32cred)
CREDUI_FLAGS.doc ("Options for username prompt UI")
CRED_FLAGS = constants.Constants.from_pattern (u"CRED_FLAGS_*", namespace=win32cred)
CRED_TYPE = constants.Constants.from_pattern (u"CRED_TYPE_*", namespace=win32cred)
CRED_TI = constants.Constants.from_pattern (u"CRED_TI_*", namespace=win32cred)
WELL_KNOWN_SID = constants.Constants.from_pattern (u"Win*Sid")
WELL_KNOWN_SID.doc ("Well-known SIDs common to all computers")

PySID = pywintypes.SIDType

class x_accounts (exc.x_winsys):
  "Base for all accounts-related exceptions"

WINERROR_MAP = {
  winerror.ERROR_NONE_MAPPED : exc.x_not_found
}
wrapped = exc.wrapper (WINERROR_MAP, x_accounts)

def principal (principal):
  ur"""Factory function for the :class:`Principal` class. This is the most
  common way to create a :class:`Principal` object::
  
    from winsys import accounts
    authenticated_users = accounts.principal (accounts.WELL_KNOWN_SID.AuthenticatedUser)
    local_admin = accounts.principal ("Administrator")
    domain_users = accounts.principal (r"DOMAIN\Domain Users")
  
  :param principal: any of None, a :class:`Principal`, a `PySID`, a :const:`WELL_KNOWN_SID` or a string
  :returns: a :class:`Principal` object corresponding to `principal`
  """
  if principal is None:
    return None
  elif type (principal) == PySID:
    return Principal (principal)
  elif isinstance (principal, int):
    return Principal.from_well_known (principal)
  elif isinstance (principal, Principal):
    return principal
  else:
    return Principal.from_string (unicode (principal))

def me ():
  ur"""Convenience function for the common case of getting the
  logged-on user's account.
  """
  return Principal.me ()

class Principal (core._WinSysObject):
  u"""Object wrapping a Windows security principal, represented by a SID
  and, where possible, a name.
  """

  def __init__ (self, sid, system_name=None):
    u"""Initialise a Principal from and (optionally) a system name. The sid
    must be a PySID and the system name, if present must be a security
    authority, eg a machine or a domain.
    """
    core._WinSysObject.__init__ (self)
    self.sid = sid
    try:
      self.name, self.domain, self.type = wrapped (win32security.LookupAccountSid, system_name, self.sid)
    except exc.x_not_found:
      self.name = str (self.sid)
      self.domain = self.type = None

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
    
    (EXPERIMENTAL) If no password is given, a UI pops up
    to ask for a password.
    
    :param password: the password for this account
    :param logon_type: one of the :const:`LOGON` values
    :returns: a pywin32 handle to a logon session
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
    ur"""Return a :class:`Principal` based on a name and a
    security authority. If `string` is blank, the logged-on user is assumed.
    
    :param string: name of an account in the form "domain\name". domain is optional so the simplest form is simply "name"
    :param system_name: name of a security authority (typically a machine or a domain)
    :returns: a :class:`Principal` object for `string`
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
  def from_well_known (cls, well_known, domain=None):
    ur"""Return a :class:`Principal` based on one of the :const:`WELL_KNOWN_SID` values.
    
    :param well_known: one of the :const:`WELL_KNOWN_SID`
    :param domain: anything accepted by :func:`principal` and corresponding to a domain
    """
    return cls (wrapped (win32security.CreateWellKnownSid, well_known, principal (domain)))

  @classmethod
  def me (cls):
    u"""Convenience factory method for the common case of referring to the 
    logged-on user
    """
    return cls.from_string (wrapped (win32api.GetUserNameEx, EXTENDED_NAME.SamCompatible))
    
  @contextlib.contextmanager
  def impersonate (self, password=core.UNSET, logon_type=core.UNSET):
    """Context-managed function to impersonate this user and then
    revert. Note that the :class:`Principal` is its own context manager
    so this function is rarely needed. FIXME: Is it needed at all?
    
    :param password: password for this account
    :param logon_type: one of the :const:`LOGON` values
    """
    hLogon = self.logon (password, logon_type)
    wrapped (win32security.ImpersonateLoggedOnUser, hLogon)
    yield hLogon
    wrapped (win32security.RevertToSelf)
    
  def __enter__ (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.logon (logon_type=LOGON.LOGON_INTERACTIVE))
  
  def __exit__ (self, *exc_info):
    wrapped (win32security.RevertToSelf)

class User (Principal):
  """(UNUSED) User subclass"""
  
class Group (Principal):
  """(UNUSED) Group subclass"""

