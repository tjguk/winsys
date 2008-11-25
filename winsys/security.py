# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys
import contextlib
import operator

import win32security
import win32api
import pywintypes
import winerror

from winsys import core, utils, accounts, _aces, _acls, _privileges
from winsys.constants import *
from winsys.exceptions import *

PyHANDLE = pywintypes.HANDLEType
PyACL = pywintypes.ACLType
PySECURITY_ATTRIBUTES = pywintypes.SECURITY_ATTRIBUTESType

class x_security (x_winsys):
  pass

class x_value_not_set (x_security):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_security)

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
    
class Security (core._WinSysObject):

  OPTIONS = {
    u"O" : SECURITY_INFORMATION.OWNER,
    u"G" : SECURITY_INFORMATION.GROUP,
    u"D" : SECURITY_INFORMATION.DACL,
    u"S" : SECURITY_INFORMATION.SACL
  }
  DEFAULT_OPTIONS = u"OD"
  DEFAULT_CONTROL = SD_CONTROL.SELF_RELATIVE
  
  def __init__ (
    self,
    control=DEFAULT_CONTROL,
    owner=None,
    group=None,
    dacl=None,
    sacl=None,
    inherit_handle=True,
    originating_object=None,
    originating_object_type=None
  ):
    core._WinSysObject.__init__ (self)
    self._control = control
    self._owner = None
    self._group = None
    self._dacl = None
    self._sacl = None
    self.inherit_handle = inherit_handle
    self._originating_object = originating_object
    self._originating_object_type = originating_object_type
    
    if owner is not None:
      self.owner = owner
    if group is not None:
      self.group = group
    if dacl is not None:
      self.dacl = dacl
    if sacl is not None:
      self.sacl = sacl

    self.inherits = not bool (self._control & SD_CONTROL.DACL_PROTECTED)

  def as_string (self):
    security_information = 0
    if self._owner:
      security_information |= SECURITY_INFORMATION.OWNER
    if self._group:
      security_information |= SECURITY_INFORMATION.GROUP
    if self._dacl:
      security_information |= SECURITY_INFORMATION.DACL
    if self._sacl:
      security_information |= SECURITY_INFORMATION.SACL
    sa = self.pyobject (include_inherited=True)
    return wrapped (
      win32security.ConvertSecurityDescriptorToStringSecurityDescriptor,
      sa.SECURITY_DESCRIPTOR,
      REVISION.SDDL_REVISION_1, 
      security_information
    )
    
  def dumped (self, level):
    output = []
    if self._control is not None: output.append (u"control:\n%s" % utils.dumped_flags (self._control, SD_CONTROL, level))
    if self._owner is not None: output.append (u"owner: %s" % self.owner)
    if self._group is not None: output.append (u"group: %s" % self.group)
    if self._dacl is not None: output.append (u"dacl:\n%s" % self.dacl.dumped (level))
    if self._sacl is not None: output.append (u"sacl:\n%s" % self.sacl.dumped (level))
    return utils.indented (u"\n".join (output), level)
  
  def break_inheritance (self, copy_first=True):
    if copy_first and self.dacl:
      for ace in self.dacl:
        ace.inherited = False
    else:
      self.dacl = [a for a in (self.dacl or []) if not a.inherited]
    self.inherits = False

  def restore_inheritance (self):
    self.inherits = True
    self.dacl = self.dacl
  
  def _get_owner (self):
    if self._owner is None:
      raise x_value_not_set (u"No Owner has been set for this Security object")
    return self._owner
  def _set_owner (self, owner):
    self._owner = accounts.principal (owner)
  owner = property (_get_owner, _set_owner)

  def _get_group (self):
    if self._group is None:
      raise x_value_not_set (u"No Group has been set for this Security object")
    return self._group
  def _set_group (self, group):
    self._group = accounts.principal (group)
  group = property (_get_group, _set_group)

  def _get_dacl (self):
    if self._dacl is None:
      raise x_value_not_set (u"No DACL has been set for this Security object")
    return self._dacl
  def _set_dacl (self, dacl):
    self._dacl = _acls.acl (dacl)
  dacl = property (_get_dacl, _set_dacl)

  def _get_sacl (self):
    if self._sacl is None:
      raise x_value_not_set (u"No SACL has been set for this Security object")
    return self._sacl
  def _set_sacl (self, sacl):
    self._sacl = _acls.acl (sacl)
  sacl = property (_get_sacl, _set_sacl)

  def __enter__ (self):
    if not self._originating_object:
      raise x_winsys (u"Cannot run anonymous security within a context")
    return self

  def __exit__ (self, exc_type, exc_value, traceback):
    if exc_type is None:
      self.to_object ()
      return True
    else:
      return False
      
  @classmethod
  def _options (cls, options):
    try:
      return int (options)
    except ValueError:
      return reduce (operator.or_, (cls.OPTIONS[opt] for opt in options.upper ()), 0)
      
  def to_object (self, obj=None, object_type=None, options=None):
    u"""Write the current state of the object as the security settings
    on a Windows object, typically a file.
    
    obj - name of the object (eg, a filepath)
    object_type - from SE_OBJECT_TYPE
    options - None to update whatever's changed; OR an or-ing of SECURITY_INFORMATION
      constants; OR a string containing some or all of "OGDS" for Owner, Group,
      DACL, SACL respectively.
    """
    obj = obj or self._originating_object
    if not obj:
      raise exceptions.x_winsys (u"No object to write security to")
    object_type = object_type or self._originating_object_type or SE_OBJECT_TYPE.FILE_OBJECT

    if options is None:
      options = 0
      if self._owner is not None:
        options |= SECURITY_INFORMATION.OWNER
      if self._group is not None:
        options |= SECURITY_INFORMATION.GROUP
      if self._dacl is not None:
        options |= SECURITY_INFORMATION.DACL
        if self.inherits:
          options |= SECURITY_INFORMATION.UNPROTECTED_DACL
        else:
          options |= SECURITY_INFORMATION.PROTECTED_DACL
      if self._sacl is not None:
        options |= SECURITY_INFORMATION.SACL
        if self.inherits:
          options |= SECURITY_INFORMATION.UNPROTECTED_SACL
        else:
          options |= SECURITY_INFORMATION.PROTECTED_SACL
    
    else:
      options = self._options (options)

    sa = self.pyobject ()
    if isinstance (obj, PyHANDLE):
      wrapped (
        win32security.SetSecurityInfo,
        obj, object_type, options,
        sa.GetSecurityDescriptorOwner (),
        sa.GetSecurityDescriptorGroup (),
        sa.GetSecurityDescriptorDacl (),
        sa.GetSecurityDescriptorSacl ()
      )
    else:
      wrapped (
        win32security.SetNamedSecurityInfo,
        obj, object_type, options,
        sa.GetSecurityDescriptorOwner (),
        sa.GetSecurityDescriptorGroup (),
        sa.GetSecurityDescriptorDacl (),
        sa.GetSecurityDescriptorSacl ()
      )
  
  def pyobject (self, include_inherited=False):
    sa = wrapped (win32security.SECURITY_ATTRIBUTES)
    sa.bInheritHandle = self.inherit_handle
    owner = None if self._owner is None else self._owner.pyobject ()
    group = None if self._group is None else self._group.pyobject ()
    dacl = None if self._dacl is None else self._dacl.pyobject (include_inherited=include_inherited)
    sacl = None if self._sacl is None else self._sacl.pyobject (include_inherited=include_inherited)
    if owner:
      sa.SetSecurityDescriptorOwner (owner, False)
    if group:
      sa.SetSecurityDescriptorGroup (group, False)
    #
    # The first & last flags on the Set...acl methods represent,
    # respectively, whether the ACL is present (!) and whether
    # it's the result of inheritance.
    #
    sa.SetSecurityDescriptorDacl (True, dacl, False)
    sa.SetSecurityDescriptorSacl (True, sacl, False)
    if self.inherits:
      sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, 0)
    else:
      sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, SD_CONTROL.DACL_PROTECTED)
    return sa

  @classmethod
  def from_object (cls, obj, object_type=SE_OBJECT_TYPE.FILE_OBJECT, options=DEFAULT_OPTIONS):
    options = cls._options (options)
    if isinstance (obj, PyHANDLE):
      sd = wrapped (win32security.GetSecurityInfo, obj, object_type, options)
    else:
      sd = wrapped (win32security.GetNamedSecurityInfo, obj, object_type, options)
    return cls.from_security_descriptor (
      sd, 
      originating_object=obj, 
      originating_object_type=object_type, 
      options=options
    )

  @classmethod
  def from_security_descriptor (
    cls, 
    sd, 
    inherit_handle=True, 
    originating_object=None, 
    originating_object_type=None, 
    options=DEFAULT_OPTIONS
  ):
    u"""Factory method to construct a Security object from a PySECURITY_DESCRIPTOR
    object.

    @param sd A PySECURITY_DESCRIPTOR instance
    @param inherit_handle A flag indicating whether the handle is to be inherited
    @return a Security instance
    """
    options = cls._options (options)
    control, revision = sd.GetSecurityDescriptorControl ()
    owner = sd.GetSecurityDescriptorOwner () if SECURITY_INFORMATION.OWNER & options else None
    group = sd.GetSecurityDescriptorGroup () if SECURITY_INFORMATION.GROUP & options else None
    dacl = sd.GetSecurityDescriptorDacl () if SECURITY_INFORMATION.DACL & options else None
    sacl = sd.GetSecurityDescriptorSacl () if SECURITY_INFORMATION.SACL & options else None
    return cls (
      control,
      owner, group, dacl, sacl,
      inherit_handle,
      originating_object, originating_object_type
    )

  @classmethod
  def from_string (cls, sddl, options=DEFAULT_OPTIONS):
    u"""Factory method to construct a Security object from a string in
    Microsoft SDDL format.

    @param string A string in Microsoft SDDL format
    @return A Security instance
    """
    return cls.from_security_descriptor (
      sd=wrapped (
        win32security.ConvertStringSecurityDescriptorToSecurityDescriptor,
        unicode (string),
        REVISION.SDDL_REVISION_1
      ), 
      options=options
    )

def security (obj=object, obj_type=None, options=Security.DEFAULT_OPTIONS):
  if obj is None:
    return None
  elif obj is object:
    return Security ()
  elif isinstance (obj, Security):
    return obj
  elif isinstance (obj, PyHANDLE):
    return Security.from_object (obj, obj_type, options=options)
  elif isinstance (obj, PySECURITY_ATTRIBUTES):
    return Security.from_security_descriptor (obj, options=options)
  else:
    return Security.from_object (unicode (obj), object_type=SE_OBJECT_TYPE.FILE_OBJECT, options=options)

class LogonSession (core._WinSysObject):
  
  _MAP = {
    u"UserName" : accounts.principal,
    u"Sid" : accounts.principal,
    u"LogonTime" : utils.from_pytime
  }
  
  def __init__ (self, session_id):
    core._WinSysObject.__init__ (self)
    self._session_id = session_id
    self._session_info = {}
    for k, v in wrapepd (win32security.LsaGetLogonSessionData, session_id).items ():
      mapper = self._MAP.get (k)
      if mapper: v = mapper (v)
      self._session_info[k] = v
    
  def __getattr__ (self, attr):
    return self._session_info[attr]
    
  def __dir__ (self):
    return self._session_info.keys ()
    
  def as_string (self):
    return u"Logon Session for %(UserName)s" % self._session_info
    
  def dumped (self, level):
    output = []
    output.append (u"session_id: %s" % self._session_id)
    output.append (u"UserName: %s" % self.UserName)
    output.append (u"Sid: %s" % (self.Sid.sid if self.Sid else None))
    output.append (u"LogonTime: %s" % self.LogonTime)
    return utils.dumped ("\n".join (output), level)

class LSA (core._WinSysObject):
  
  def __init__ (self, system_name=None):
    core._WinSysObject.__init__ (self)
    self._lsa = wrapped (win32security.LsaOpenPolicy, system_name, 0)
  
  @staticmethod
  def logon_sessions ():
    for session_id in wrapped (win32security.LsaEnumerateLogonSessions):
      yield LogonSession (session_id)

#
# Friendly constructors
#
def token (token):
  if token is None:
    return None
  elif type (token) is PyHANDLE:
    return Token (token)
  elif issubclass (token.__class__, Token):
    return token
  else:
    raise x_winsys (u"Token must be HANDLE, Token or None")

#
# Convenience functions
#

@contextlib.contextmanager
def impersonate (user, password):
  impersonation_token = token (accounts.principal (user).logon (password)).impersonate ()
  yield impersonation_token
  impersonation_token.unimpersonate ()

@contextlib.contextmanager
def change_privileges (enable_privs=[], disable_privs=[], token=None):
  if token is None:
    token = Token.from_thread ()
  old_enabled_privs, old_disabled_privs = token.change_privileges (enable_privs, disable_privs)
  yield token
  token.change_privileges (old_enabled_privs, old_disabled_privs)

if __name__ == '__main__':
  Token.from_thread ().dump ()
