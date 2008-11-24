# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys
import contextlib
import operator

import win32security
import win32api
import pywintypes
import winerror

from winsys import core, utils, accounts
from winsys.constants import *
from winsys.exceptions import *

PyHANDLE = pywintypes.HANDLEType
PyACL = pywintypes.ACLType
PySECURITY_ATTRIBUTES = pywintypes.SECURITY_ATTRIBUTESType

class x_security (x_winsys):
  pass

class x_access_denied (x_security):
  pass
  
class x_value_not_set (x_security):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_security)

class _SecurityObject (core._WinSysObject):
  u"""Base class behind all of the security classes.
  Each class is expected to wrap an underlying Windows
  structure, probably represented by a pywin32 object,
  altho' possibly implemented by ctypes.
  """
  def pyobject (self):
    u"""This should return the underlying -- probably
    pywin32-based -- object, usually after calling 
    copying the presentation data back out.
    
    By default it is not implemented 
    """
    raise NotImplementedError
  
  def raw (self):
    u"""Intended where a pywin32 object offers a buffer
    interface to its underlying data.
    
    By default it is not implemented
    """
    raise NotImplementedError

class Privilege (_SecurityObject):

  def __init__ (self, luid, attributes=0):
    u"""luid is one of the PRIVILEGE_NAME constants
    attributes is the result of or-ing the different PRIVILEGE_ATTRIBUTE items you want
    """
    _SecurityObject.__init__ (self)
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
  
class Token (_SecurityObject):

  def __init__ (self, hToken, hProcess=None, hThread=None):
    _SecurityObject.__init__ (self)
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
      self._info[u'privileges'] = [Privilege (luid, a) for (luid, a) in self.info (u"Privileges")]
    if attr == u"PrimaryGroup" or attr is None:
      self._info[u'primary_group'] = accounts.principal (self.info (u"PrimaryGroup"))
    if attr == u"Source" or attr is None:
      try:
        self._info[u'source'] = self.info (u"Source")
      except x_access_denied:
        self._info[u'source'] = None
    if attr == u"DefaultDacl" or attr is None:
      self._info[u'default_dacl'] = DACL (self.info (u"DefaultDacl"))
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
    privs.extend ((privilege (p).pyobject (), PRIVILEGE_ATTRIBUTE.ENABLED) for p in enable_privs)
    privs.extend ((privilege (p).pyobject (), 0) for p in disable_privs)
    old_privs = wrapped (win32security.AdjustTokenPrivileges, self.hToken, 0, privs)
    self._refresh (u"Privileges")
    return (
      [privilege (priv) for (priv, status) in old_privs if status == PRIVILEGE_ATTRIBUTE.ENABLED],
      [privilege (priv) for (priv, status) in old_privs if status == 0]
    )
      
  def impersonate (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.hToken)
    return self

  def unimpersonate (self):
    wrapped (win32security.RevertToSelf)
    
class ACE (_SecurityObject):

  ACCESS = {
    u"R" : GENERIC_ACCESS.READ,
    u"W" : GENERIC_ACCESS.WRITE,
    u"X" : GENERIC_ACCESS.EXECUTE,
    u"C" : GENERIC_ACCESS.READ | GENERIC_ACCESS.WRITE | GENERIC_ACCESS.EXECUTE,
    u"F" : GENERIC_ACCESS.ALL
  }
  TYPES = {
    u"ALLOW" : ACE_TYPE.ACCESS_ALLOWED,
    u"DENY" : ACE_TYPE.ACCESS_DENIED
  }
  FLAGS = ACE_FLAG.OBJECT_INHERIT | ACE_FLAG.CONTAINER_INHERIT
  
  def __init__ (self, trustee, access, type, flags=FLAGS, object_type=None, inherited_object_type=None):
    u"""Construct a new ACE

    @param trustee "domain \ user" or Principal instance representing the security principal
    @param access Bitmask or "RWXCF"
    @param type "ALLOW" or "DENY" or number representing one of the *_ACE_TYPE constants
    @param flags Bitmask or Set of strings or numbers representing the AceFlags constants
    """
    _SecurityObject.__init__ (self)
    self.type = type
    self.is_allowed = type in (ACE_TYPE.ACCESS_ALLOWED, ACE_TYPE.ACCESS_ALLOWED_OBJECT)
    self._trustee = trustee
    self._access_mask = access
    self._flags = flags
    self.object_type = object_type
    self.inherited_object_type = inherited_object_type
    
  def _id (self):
    return (self.trustee, self.access, self.type)

  def __eq__ (self, other):
    return (self.trustee, self.access, self.type) == (other.trustee, other.access, other.type)
    
  def __lt__ (self, other):
    u"""Deny comes first, then what?"""
    return (self.is_allowed < other.is_allowed)
    
  def as_string (self):
    type = ACE_TYPE.name_from_value (self.type)
    flags = " | ".join (ACE_FLAG.names_from_value (self._flags))
    access = utils.mask_as_string (self.access)
    return u"%s %s %s %s" % (self.trustee, access, flags, type)

  def dumped (self, level):
    output = []
    output.append (u"trustee: %s" % self.trustee)
    output.append (u"access: %s" % utils.mask_as_string (self.access))
    output.append (u"type: %s" % ACE_TYPE.name_from_value (self.type))
    if self._flags:
      output.append (u"flags:\n%s" % utils.dumped_flags (self._flags, ACE_FLAG, level))
    return utils.dumped (u"\n".join (output), level)
  
  def _get_inherited (self):
    return bool (self._flags & ACE_FLAG.INHERITED)
  def _set_inherited (self, switch):
    if switch:
      self._flags |= ACE_FLAG.INHERITED
    else:
      self._flags &= ~ACE_FLAG.INHERITED
  inherited = property (_get_inherited, _set_inherited)
  
  def _get_containers_inherit (self):
    return bool (self._flags & ACE_FLAG.CONTAINER_INHERIT_ACE)
  def _set_containers_inherit (self, switch):
    if self.inherited:
      raise x_access_denied (u"Cannot change an inherited ACE")
    if switch:
      self._flags |= ACE_FLAG.CONTAINER_INHERIT
    else:
      self._flags &= ~ACE_FLAG.CONTAINER_INHERIT
  containers_inherit = property (_get_containers_inherit, _set_containers_inherit)
  
  def _get_objects_inherit (self):
    return bool (self._flags & ACE_FLAG.OBJECT_INHERIT)
  def _set_objects_inherit (self, switch):
    if self.inherited:
      raise x_access_denied (u"Cannot change an inherited ACE")
    if switch:
      self._flags |= ACE_FLAG.OBJECT_INHERIT
    else:
      self._flags &= ~ACE_FLAG.OBJECT_INHERIT
  objects_inherit = property (_get_objects_inherit, _set_objects_inherit)
  
  def _get_access (self):
    return self._access_mask
  def _set_access (self, access):
    if self.inherited:
      raise x_access_denied (u"Cannot change an inherited ACE")
    self._access_mask = self._access (access)
  access = property (_get_access, _set_access)
  
  def _get_trustee (self):
    return self._trustee
  def _set_trustee (self, trustee):
    if self.inherited:
      raise x_access_denied (u"Cannot change an inherited ACE")
    self._trustee = accounts.principal (trustee)
  trustee = property (_get_trustee, _set_trustee)
  
  @classmethod
  def from_ace (cls, ace):
    (type, flags) = ace[0]
    name = ACE_TYPE.name_from_value (type)
    if u"object" in name.lower ().split (u"_"):
      mask, object_type, inherited_object_type, sid = ace[1:]
    else:
      mask, sid = ace[1:]
      object_type = inherited_object_type = None

    if issubclass (cls, DACE):
      _class = DACE
    elif issubclass (cls, SACE):
      _class = SACE
    else:
      if name not in ACE_TYPE.names (u"ACCESS_*"):
        _class = DACE
      else:
        _class = SACE

    return _class (accounts.principal (sid), mask, type, flags, object_type, inherited_object_type)

  @classmethod
  def _access (cls, access):
    try:
      return int (access)
    except ValueError:
      return reduce (operator.or_, (cls.ACCESS[a] for a in access.upper ()), 0)
        
  @classmethod
  def _type (cls, type):
    return cls.TYPES[type]
  
  @classmethod
  def from_tuple (cls, ace_info):
    (trustee, access, allow_or_deny) = ace_info
    return cls (accounts.principal (trustee), cls._access (access), cls._type (allow_or_deny))

  def as_tuple (self):
    return self.type, self.trustee, self.access, self._flags

class DACE (ACE):
  pass

class SACE (ACE):
  pass

class ACL (_SecurityObject):

  _ACE = ACE
  _ACE_MAP = {
    ACE_TYPE.ACCESS_ALLOWED : u"AddAccessAllowedAceEx",
    ACE_TYPE.ACCESS_DENIED : u"AddAccessDeniedAceEx"
  }

  def __init__ (self, acl=None):
    _SecurityObject.__init__ (self)
    if acl is None:
      self._list = None
    else:
      self._list = list (self._ACE.from_ace (acl.GetAce (index)) for index in range (acl.GetAceCount ()))

  def dumped (self, level=0):
    output = []
    for ace in self._list or []:
      output.append (ace.dumped (level))
    return utils.dumped (u"\n".join (output), level)

  def __iter__ (self):
    if self._list is None:
      raise x_value_not_set (u"No entry has been set for this ACL")
    else:
      return iter (sorted (self._list))

  def append (self, _ace):
    self._list.append (ace (_ace))

  def __getitem__ (self, index):
    return self._list[index]

  def __setitem__ (self, index, item):
    self._list[index] = ace (item)

  def __delitem__ (self, index):
    del self._list[index]

  def __getattr__ (self, attr):
    return getattr (self._list, attr)

  def __len__ (self):
    return len (self._list or [])

  def __nonzero__ (self):
    return bool (self._list)

  def as_string (self):
    return repr (self._list)
  
  def __contains__ (self, a):
    return ace (a) in (self._list or [])

  def pyobject (self):
    if self._list is None:
      return None
    
    acl = wrapped (win32security.ACL)
    aces = sorted (a for a in self._list if not a.inherited)
    for ace in aces:
      adder_fn = self._ACE_MAP.get (ace.type)
      if adder_fn:
        adder = getattr (acl, adder_fn)
        adder (REVISION.ACL_REVISION_DS, ace._flags, ace.access, ace.trustee.pyobject ())
      else:
        raise NotImplementedError
    return acl
    
  @classmethod
  def from_list (cls, aces):
    acl = cls (wrapped (win32security.ACL))
    for a in aces:
      acl.append (ace (a))
    return acl
  
  @classmethod
  def public (cls):
    return cls.from_list ([(u"Everyone", u"F", u"ALLOW")])
    
  @classmethod
  def private (cls):
    return cls.from_list ([("", u"F", u"ALLOW")])

class DACL (ACL):
  _ACE = DACE

class SACL (ACL):
  _ACE = SACE

class Security (_SecurityObject):

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
    _SecurityObject.__init__ (self)
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
    print "as_string", security_information
    return wrapped (
      win32security.ConvertSecurityDescriptorToStringSecurityDescriptor,
      self.pyobject ().SECURITY_DESCRIPTOR,
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
    self._dacl = acl (dacl)
  dacl = property (_get_dacl, _set_dacl)

  def _get_sacl (self):
    if self._sacl is None:
      raise x_value_not_set (u"No SACL has been set for this Security object")
    return self._sacl
  def _set_sacl (self, sacl):
    self._sacl = acl (sacl)
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
  
  def pyobject (self):
    sa = wrapped (win32security.SECURITY_ATTRIBUTES)
    sa.bInheritHandle = self.inherit_handle
    owner = None if self._owner is None else self._owner.pyobject ()
    group = None if self._group is None else self._group.pyobject ()
    dacl = None if self._dacl is None else self._dacl.pyobject ()
    sacl = None if self._sacl is None else self._sacl.pyobject ()
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

class LogonSession (_SecurityObject):
  
  _MAP = {
    u"UserName" : accounts.principal,
    u"Sid" : accounts.principal,
    u"LogonTime" : utils.from_pytime
  }
  
  def __init__ (self, session_id):
    _SecurityObject.__init__ (self)
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

class LSA (_SecurityObject):
  
  def __init__ (self, system_name=None):
    _SecurityObject.__init__ (self)
    self._lsa = wrapped (win32security.LsaOpenPolicy, system_name, 0)
  
  @staticmethod
  def logon_sessions ():
    for session_id in wrapped (win32security.LsaEnumerateLogonSessions):
      yield LogonSession (session_id)

#
# Friendly constructors
#

def privilege (privilege):
  u"""Friendly constructor for the Privilege class"""
  if issubclass (privilege.__class__, Privilege):
    return privilege
  elif issubclass (privilege.__class__, int):
    return Privilege (privilege)
  else:
    return Privilege.from_string (unicode (privilege))

def ace (ace):
  if ace is None:
    return None
  elif issubclass (ace.__class__, ACE):
    return ace
  else:
    return ACE.from_tuple (tuple (ace))

def acl (acl):
  if acl is None:
    return ACL (None)
  elif type (acl) is PyACL:
    return ACL (acl)
  elif issubclass (acl.__class__, ACL):
    return acl
  else:
    return ACL.from_list (iter (acl))
    
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
