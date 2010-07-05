# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys

import win32security
import win32api
import winerror
import pywintypes

from winsys import accounts, constants, core, exc, utils
from winsys._security import _privileges, _aces, _acls

__all__ = ['Token', 'token', 'x_token', 'x_no_token']

class x_token (exc.x_winsys):
  "Base for all token-related exceptions"

class x_no_token (x_token):
  "Raised when a token cannot be retrieved"

PyHANDLE = pywintypes.HANDLEType

WINERROR_MAP = {
  winerror.ERROR_ACCESS_DENIED : exc.x_access_denied,
  winerror.ERROR_NO_TOKEN : x_no_token
}
wrapped = exc.wrapper (WINERROR_MAP, x_token)

def _from_sid_and_attribute (data):
  sid, attributes = data
  #
  # SDK says that no attributes are defined at present,
  # so ignore them!
  #
  return accounts.principal (sid)

def _from_sid_and_attributes (data):
  return [_from_sid_and_attribute (d) for d in data]

def _from_privileges (data):
  return [_privileges.Privilege (*d) for d in data]

class Token (core._WinSysObject):

  _MAP = {
    "User" : _from_sid_and_attribute,
    "Owner" : accounts.principal,
    "Groups" : _from_sid_and_attributes,
    "RestrictedSids" : _from_sid_and_attributes,
    "Privileges" : _from_privileges,
    "PrimaryGroup" : accounts.principal,
    "DefaultDacl" : _acls.acl,
  }

  def __init__ (self, hToken, hProcess=None, hThread=None):
    core._WinSysObject.__init__ (self)
    self.hToken = hToken
    self.hProcess = hProcess
    self.hThread = hThread

  def __getattr__ (self, attr):
    info_type = getattr (win32security, "Token" + attr)
    fn = self._MAP.get (attr, lambda x : x)
    return fn (wrapped (win32security.GetTokenInformation, self.hToken, info_type))

  def as_string (self):
    return "%s in process/thread %s/%s" % (self.User, self.hProcess, self.hThread)

  def dumped (self, level):
    output = []
    output.append ("user: %s" % self.User)
    output.append ("owner: %s" % self.Owner)
    output.append ("groups:\n%s" % utils.dumped_list (self.Groups, level))
    output.append ("restricted_sids:\n%s" % utils.dumped_list (self.RestrictedSids, level))
    output.append ("privileges:\n%s" % utils.dumped_list (sorted (self.Privileges), level))
    output.append ("primary_group: %s" % self.PrimaryGroup)
    output.append ("source: %s, %s" % self.Source)
    output.append ("default_dacl:\n%s" % self.DefaultDacl.dumped (level))
    output.append ("type: %s" % self.Type)
    output.append ("session_id: %s" % self.SessionId)
    output.append ("statistics:\n%s" % utils.dumped_dict (self.Statistics, level))
    return utils.dumped ("\n".join (output), level)

  def pyobject (self):
    return self.hToken

  @classmethod
  def from_thread (cls, access=constants.GENERAL.MAXIMUM_ALLOWED):
    hProcess = win32api.GetCurrentProcess ()
    hThread = win32api.GetCurrentThread ()
    try:
      return cls (wrapped (win32security.OpenThreadToken, hThread, access, True), hProcess, hThread)
    except x_no_token:
      return cls (wrapped (win32security.OpenProcessToken, hProcess, access), hProcess, hThread)

  def change_privileges (self, enable_privs=[], disable_privs=[]):
    privs = []
    privs.extend ((_privileges.privilege (p).pyobject (), _privileges.PRIVILEGE_ATTRIBUTE.ENABLED) for p in enable_privs)
    privs.extend ((_privileges.privilege (p).pyobject (), 0) for p in disable_privs)
    old_privs = wrapped (win32security.AdjustTokenPrivileges, self.hToken, 0, privs)
    return (
      [_privileges.privilege (priv) for (priv, status) in old_privs if status == _privileges.PRIVILEGE_ATTRIBUTE.ENABLED],
      [_privileges.privilege (priv) for (priv, status) in old_privs if status == 0]
    )

  def impersonate (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.hToken)
    return self

  def unimpersonate (self):
    wrapped (win32security.RevertToSelf)

def token (token=core.UNSET):
  if token is None:
    return None
  elif token is core.UNSET:
    return Token.from_thread ()
  elif type (token) is PyHANDLE:
    return Token (token)
  elif issubclass (token.__class__, Token):
    return token
  else:
    raise x_winsys ("Token must be HANDLE, Token or None")
