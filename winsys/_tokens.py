# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys

import win32security
import win32api
import winerror
import pywintypes

from winsys import core, utils, accounts, _aces, _acls, _privileges
from winsys.constants import *
from winsys.exceptions import *

class x_token (x_winsys):
  pass

PyHANDLE = pywintypes.HANDLEType

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_token)

class Token (core._WinSysObject):

  def __init__ (self, hToken, hProcess=None, hThread=None):
    core._WinSysObject.__init__ (self)
    self.hToken = hToken
    self.hProcess = hProcess
    self.hThread = hThread
    self._info = {}
    self._refresh ()
    
  def _refresh (self, attr=None):
    if attr == u"User" or attr is None:
      sid, attributes = self.info (u"User")
      self._info[u'user'] = accounts.principal (sid)
    if attr == u"Owner" or attr is None:
      self._info[u'owner'] = accounts.principal (self.info (u"Owner"))
    if attr == u"Groups" or attr is None:
      self._info[u'groups'] = [accounts.principal (sid) for sid, attributes in self.info (u"Groups")]
    if attr == u"RestrictedSids" or attr is None:
      self._info[u'restricted_sids'] = [accounts.principal (sid) for sid, attributes in self.info (u"RestrictedSids")]
    if attr == u"Privileges" or attr is None:
      self._info[u'privileges'] = [_privileges.Privilege (luid, a) for (luid, a) in self.info (u"Privileges")]
    if attr == u"PrimaryGroup" or attr is None:
      self._info[u'primary_group'] = accounts.principal (self.info (u"PrimaryGroup"))
    if attr == u"Source" or attr is None:
      try:
        self._info[u'source'] = self.info (u"Source")
      except x_access_denied:
        self._info[u'source'] = None
    if attr == u"DefaultDacl" or attr is None:
      self._info[u'default_dacl'] = _acls.DACL (self.info (u"DefaultDacl"))
    if attr == u"Type" or attr is None:
      self._info[u'type'] = self.info (u"Type")
    #~ self._info['impersonation_level'] = self.info ("ImpersonationLevel")
    if attr == u"SessionId" or attr is None:
      self._info[u'session_id'] = self.info (u"SessionId")
    if attr == u"Statistics" or attr is None:
      self._info[u'statistics'] = self.info (u"Statistics")
    self._needs_refresh = False

  def __getattr__ (self, key):
    return self._info[key]

  def as_string (self):
    return u"%s in process/thread %s/%s" % (self.user, self.hProcess, self.hThread)
    
  def dumped (self, level):
    output = []
    output.append (u"user: %s" % self.user)
    output.append (u"owner: %s" % self.owner)
    output.append (u"groups:\n%s" % utils.dumped_list (self.groups, level))
    output.append (u"restricted_sids:\n%s" % utils.dumped_list (self.restricted_sids, level))
    output.append (u"privileges:\n%s" % utils.dumped_list (sorted (self.privileges), level))
    output.append (u"primary_group: %s" % self.primary_group)
    output.append (u"source: %s, %s" % self.source)
    output.append (u"default_dacl:\n%s" % self.default_dacl.dumped (level))
    output.append (u"type: %s" % self.type)
    output.append (u"session_id: %s" % self.session_id)
    output.append (u"statistics:\n%s" % utils.dumped_dict (self.statistics, level))
    return utils.dumped (u"\n".join (output), level)

  def info (self, type):
    info_type = getattr (win32security, u"Token" + type)
    try:
      return wrapped (win32security.GetTokenInformation, self.hToken, info_type)
    except x_security, (errmsg, errctx, errno):
      if errno == winerror.ERROR_ACCESS_DENIED:
        raise x_access_denied ("Access denied", repr (self), errno)
      else:
        raise

  @classmethod
  def from_thread (cls, access=GENERAL.MAXIMUM_ALLOWED):
    hProcess = win32api.GetCurrentProcess ()
    hThread = win32api.GetCurrentThread ()
    try:
      return cls (wrapped (win32security.OpenThreadToken, hThread, access, True), hProcess, hThread)
    except x_security, (errmsg, errcontext, errno):
      if errno == winerror.ERROR_NO_TOKEN:
        return cls (wrapped (win32security.OpenProcessToken, hProcess, access), hProcess, hThread)
      else:
        raise

  def change_privileges (self, enable_privs=[], disable_privs=[]):
    privs = []
    privs.extend ((_privileges.privilege (p).pyobject (), PRIVILEGE_ATTRIBUTE.ENABLED) for p in enable_privs)
    privs.extend ((_privileges.privilege (p).pyobject (), 0) for p in disable_privs)
    old_privs = wrapped (win32security.AdjustTokenPrivileges, self.hToken, 0, privs)
    self._refresh (u"Privileges")
    return (
      [_privileges.privilege (priv) for (priv, status) in old_privs if status == PRIVILEGE_ATTRIBUTE.ENABLED],
      [_privileges.privilege (priv) for (priv, status) in old_privs if status == 0]
    )
      
  def impersonate (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.hToken)
    return self

  def unimpersonate (self):
    wrapped (win32security.RevertToSelf)
    
def token (token):
  if token is None:
    return None
  elif type (token) is PyHANDLE:
    return Token (token)
  elif issubclass (token.__class__, Token):
    return token
  else:
    raise x_winsys (u"Token must be HANDLE, Token or None")
