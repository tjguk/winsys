# -*- coding: iso-8859-1 -*-
ur"""Object permissions, user accounts and process privileges

Windows manages security by granting rights -- such as the
ability to read or write from an object -- in the form of
Access Control Lists (ACLs) of Access Control Entries (ACEs)
to specific security principals: users, groups or other entities.
In addition, process security is managed by granting each logged-on
session a Token which contains the rights associated with that
session plus certain Privileges, such as the ability to take
ownership of any object or to access security-related data.

ACLs and ACEs are managed through the :class:`Security` object,
accessed mostly by means of the :func:`security` function, or
the :meth:`fs.Entry.security` method on external classes. Security
principals are represented by :class:`Principal` objects, accessed
via the :func:`principal` function. :class:`Privilege` objects
refer to process privileges and are reached through the :func:`principal`
function, or through the :attr:`Privileges` attribute of a :class:`Token`.
"""
from __future__ import with_statement
import os, sys
import contextlib
import operator

import win32security
import win32api
import win32con
import win32process
import pywintypes
import winerror

#
# For ease of management, the bulk of the security module
# has been split into submodules contained within a
# subpackage. For convenience in access, these are all
# imported into the security module which is intended to
# be the normal means of accessing these functions,
# classes, constants, etc. However, they may each be
# imported individually if needs be.
#
from winsys import constants, core, exc, utils
from winsys._security.core import REVISION
from winsys._security._tokens import *
from winsys._security._aces import *
from winsys._security._acls import *
from winsys._security._privileges import *
from winsys.accounts import *

SE_OBJECT_TYPE = constants.Constants.from_list ([
  u"SE_UNKNOWN_OBJECT_TYPE",
  u"SE_FILE_OBJECT",
  u"SE_SERVICE",
  u"SE_PRINTER",
  u"SE_REGISTRY_KEY",
  u"SE_LMSHARE",
  u"SE_KERNEL_OBJECT",
  u"SE_WINDOW_OBJECT",
  u"SE_DS_OBJECT",
  u"SE_DS_OBJECT_ALL",
  u"SE_PROVIDER_DEFINED_OBJECT",
  u"SE_WMIGUID_OBJECT",
  u"SE_REGISTRY_WOW64_32KEY"
], pattern=u"SE_*", namespace=win32security)
SE_OBJECT_TYPE.doc (u"Types of object which can be secured")
SECURITY_INFORMATION = constants.Constants.from_pattern (
  u"*_SECURITY_INFORMATION", 
  namespace=win32security
)
SECURITY_INFORMATION.doc (u"Information held with a security descriptor body")
SD_CONTROL = constants.Constants.from_list ([
  #~ "SE_DACL_AUTO_INHERIT_REQ", 
  u"SE_DACL_AUTO_INHERITED", 
  u"SE_DACL_DEFAULTED", 
  u"SE_DACL_PRESENT", 
  u"SE_DACL_PROTECTED", 
  u"SE_GROUP_DEFAULTED",
  u"SE_OWNER_DEFAULTED",
  #~ "SE_RM_CONTROL_VALID",
  #~ "SE_SACL_AUTO_INHERIT_REQ",
  u"SE_SACL_AUTO_INHERITED",
  u"SE_SACL_DEFAULTED",
  u"SE_SACL_PRESENT",
  u"SE_SACL_PROTECTED",
  u"SE_SELF_RELATIVE"
], pattern=u"SE_*", namespace=win32security)
SD_CONTROL.doc (u"Information held with a security descriptor header")

PyHANDLE = pywintypes.HANDLEType
PySECURITY_ATTRIBUTES = pywintypes.SECURITY_ATTRIBUTESType
PySECURITY_DESCRIPTOR = type (pywintypes.SECURITY_DESCRIPTOR ())

class x_security (exc.x_winsys):
  u"Base for security-related exceptions"

class x_value_not_set (x_security):
  u"Raised if an attempt is made to read a security value which hasn't been set"

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_security)

class Security (core._WinSysObject):

  OPTIONS = {
    u"O" : SECURITY_INFORMATION.OWNER,
    u"G" : SECURITY_INFORMATION.GROUP,
    u"D" : SECURITY_INFORMATION.DACL,
    u"S" : SECURITY_INFORMATION.SACL
  }
  u"""Mapping between characters and security info:
  
  * O - Owner
  * G - Group
  * D - DACL
  * S - SACL
  """
  DEFAULT_OPTIONS = u"OD"
  DEFAULT_CONTROL = SD_CONTROL.SELF_RELATIVE
  
  def __init__ (
    self,
    control=core.UNSET,
    owner=core.UNSET,
    group=core.UNSET,
    dacl=core.UNSET,
    sacl=core.UNSET,
    inherit_handle=True,
    originating_object=core.UNSET,
    originating_object_type=core.UNSET
  ):
    core._WinSysObject.__init__ (self)
    if control is core.UNSET: control = self.DEFAULT_CONTROL
    self._control = control
    self._owner = core.UNSET
    self._group = core.UNSET
    self._dacl = core.UNSET
    self._sacl = core.UNSET
    self.inherit_handle = inherit_handle
    self._originating_object = originating_object
    self._originating_object_type = originating_object_type
    
    if owner is not core.UNSET:
      self.owner = owner
    if group is not core.UNSET:
      self.group = group
    if dacl is not core.UNSET:
      self.dacl = dacl
    if sacl is not core.UNSET:
      self.sacl = sacl

  def __eq__ (self, other):
    return str (self) == str (other)
  
  def as_string (self):
    security_information = 0
    if self._owner is not core.UNSET:
      security_information |= SECURITY_INFORMATION.OWNER
    if self._group is not core.UNSET:
      security_information |= SECURITY_INFORMATION.GROUP
    if self._dacl is not core.UNSET:
      security_information |= SECURITY_INFORMATION.DACL
    if self._sacl is not core.UNSET:
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
    if self._control is not core.UNSET: 
      output.append (u"control:\n%s" % utils.dumped_flags (self._control, SD_CONTROL, level))
    if self._owner is not core.UNSET: 
      output.append (u"owner: %s" % self.owner)
    if self._group is not core.UNSET: 
      output.append (u"group: %s" % self.group)
    if self._dacl is not core.UNSET: 
      output.append (u"dacl:\n%s" % self.dacl.dumped (level))
    if self._sacl is not core.UNSET: 
      output.append (u"sacl:\n%s" % self.sacl.dumped (level))
    return utils.indented (u"\n".join (output), level)

  def break_inheritance (self, copy_first=True, break_dacl=True, break_sacl=True):
    if break_dacl and self._dacl:
      self.dacl.break_inheritance (copy_first)
    if break_sacl and self._sacl:
      self.sacl.break_inheritance (copy_first)

  def restore_inheritance (self, copy_back=True, restore_dacl=True, restore_sacl=True):
    if restore_dacl and self._dacl:
      self.dacl.restore_inheritance (copy_back)
    if restore_sacl and self._sacl:
      self.sacl.restore_inheritance (copy_back)
  
  def _get_owner (self):
    if self._owner is core.UNSET:
      raise x_value_not_set (core.UNSET, "Security._get_owner", u"No Owner has been set for this Security object")
    return self._owner
  def _set_owner (self, owner):
    if owner is None:
      raise x_value_not_set (core.UNSET, "Security._set_owner", u"Cannot set owner to None for this Security object")
    self._owner = principal (owner) or core.UNSET
  owner = property (_get_owner, _set_owner)

  def _get_group (self):
    if self._group is core.UNSET:
      raise x_value_not_set (core.UNSET, "Security._get_group", u"No Group has been set for this Security object")
    return self._group
  def _set_group (self, group):
    if group is None:
      raise x_value_not_set (core.UNSET, "Security._set_group", u"Cannot set group to None for this Security object")
    self._group = principal (group) or core.UNSET
  group = property (_get_group, _set_group)

  def _get_dacl (self):
    if self._dacl is core.UNSET:
      raise x_value_not_set (core.UNSET, "Security._get_dacl", u"No DACL has been set for this Security object")
    return self._dacl
  def _set_dacl (self, dacl):
    if dacl is core.UNSET:
      self._dacl = core.UNSET
    else:
      self._dacl = acl (dacl, DACL)
  dacl = property (_get_dacl, _set_dacl)

  def _get_sacl (self):
    if self._sacl is core.UNSET:
      raise x_value_not_set (core.UNSET, "Security._get_sacl", u"No SACL has been set for this Security object")
    return self._sacl
  def _set_sacl (self, sacl):
    if sacl is core.UNSET:
      self._sacl = core.UNSET
    else:
      self._sacl = acl (sacl, SACL)
  sacl = property (_get_sacl, _set_sacl)

  def __enter__ (self):
    if not self._originating_object:
      raise x_security (core.UNSET, "Security.__enter__", u"Cannot run anonymous security within a context")
    return self

  def __exit__ (self, exc_type, exc_value, traceback):
    if exc_type is None:
      self.to_object ()
      return True
    else:
      return False
      
  @classmethod
  def _options (cls, options):
    ur"""Accept either an integer representing a bitmask combination
    or :const:`SECURITY_INFORMATION` values; or a string whose
    characters map, via :const:`OPTIONS` to the same values.
    The following have the same result:
    
    * SECURITY_INFORMATION.OWNER | SECURITY_INFORMATION.DACL
    * "OD"
    * 0x05
    """
    try:
      return int (options)
    except ValueError:
      return reduce (operator.or_, (cls.OPTIONS[opt] for opt in options.upper ()), 0)
      
  def to_object (self, obj=core.UNSET, object_type=core.UNSET, options=core.UNSET):
    u"""Write the current state of the object as the security settings
    on a Windows object, typically a file. This is most often called
    implicitly when the :class:`Security` object is used as a context
    manager, but can be called explicitly, especially to copy one object's
    security to another::
    
      from winsys import security
      s = security.security ("filea")
      s.to_object ("fileb")
    
    :param obj: (optional) object or object name to write security to if this :class:`Security` object
                wasn't created from an object in the first place.
    :param object_type:  an :const:`SE_OBJECT_TYPE` [:const:`FILE_OBJECT`]
    :param options: anything accepted by :meth:`_options`
    """
    obj = obj or self._originating_object
    if not obj:
      raise x_security (core.UNSET, "Security.to_object", u"No object to write security to")
    object_type = object_type or self._originating_object_type or SE_OBJECT_TYPE.FILE_OBJECT

    if options is core.UNSET:
      options = 0
      if self._owner is not core.UNSET:
        options |= SECURITY_INFORMATION.OWNER
      if self._group is not core.UNSET:
        options |= SECURITY_INFORMATION.GROUP
      
      if self._dacl is not core.UNSET:
        options |= SECURITY_INFORMATION.DACL
        if self.dacl.inherited:
          options |= SECURITY_INFORMATION.UNPROTECTED_DACL
        else:
          options |= SECURITY_INFORMATION.PROTECTED_DACL
      
      if self._sacl is not core.UNSET:
        options |= SECURITY_INFORMATION.SACL
        if self.sacl.inherited:
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
    owner = None if self._owner is core.UNSET else self._owner.pyobject ()
    group = None if self._group is core.UNSET else self._group.pyobject ()
    dacl = None if self._dacl is core.UNSET else self._dacl.pyobject (include_inherited=include_inherited)
    sacl = None if self._sacl is core.UNSET else self._sacl.pyobject (include_inherited=include_inherited)
    dacl_inherited = self.dacl.inherited if dacl else 0
    sacl_inherited = self.sacl.inherited if sacl else 0
    
    sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_AUTO_INHERITED, self._control & SD_CONTROL.DACL_AUTO_INHERITED)
    sa.SetSecurityDescriptorControl (SD_CONTROL.SACL_AUTO_INHERITED, self._control & SD_CONTROL.SACL_AUTO_INHERITED)
    if dacl:
      if dacl_inherited:
        sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, 0)
      else:
        sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, SD_CONTROL.DACL_PROTECTED)
    if sacl:
      if sacl_inherited:
        sa.SetSecurityDescriptorControl (SD_CONTROL.SACL_PROTECTED, 0)
      else:
        sa.SetSecurityDescriptorControl (SD_CONTROL.SACL_PROTECTED, SD_CONTROL.SACL_PROTECTED)

    if owner:
      sa.SetSecurityDescriptorOwner (owner, False)
    if group:
      sa.SetSecurityDescriptorGroup (group, False)
    #
    # The first & last flags on the Set...acl methods represent,
    # respectively, whether the ACL is present (!) and whether
    # it's the result of inheritance.
    #
    sa.SetSecurityDescriptorDacl (True, dacl, dacl_inherited)
    sa.SetSecurityDescriptorSacl (True, sacl, sacl_inherited)
    return sa

  @classmethod
  def from_object (cls, obj, object_type=core.UNSET, options=core.UNSET):
    ur"""Constructs a :class:`Security` object from a PyHANDLE or an object name.
    Almost never called directly; use :func:`security`.
    """
    if object_type is core.UNSET: object_type = SE_OBJECT_TYPE.FILE_OBJECT
    if options is core.UNSET: options = cls.DEFAULT_OPTIONS
    
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
    originating_object=core.UNSET, 
    originating_object_type=core.UNSET, 
    options=core.UNSET
  ):
    ur"""Constructs a :class:`Security` object from a PySECURITY_DESCRIPTOR object.
    Almost never called directly; use :func:`security` unless you need some
    slightly special handling with inherited handles.
    """
    if options is core.UNSET: options = self.DEFAULT_OPTIONS
    
    options = cls._options (options)
    control, revision = sd.GetSecurityDescriptorControl ()
    owner = sd.GetSecurityDescriptorOwner () if SECURITY_INFORMATION.OWNER & options else core.UNSET
    group = sd.GetSecurityDescriptorGroup () if SECURITY_INFORMATION.GROUP & options else core.UNSET
    #
    # These next couple of lines are tricky. We have, for each ACL, three
    # situations. An ACL which simply isn't present (often the SACL); an ACL
    # which is present but which is NULL (aka the NULL ACL); an ACL which is
    # present and which is not NULL, altho' it may have nothing in it!
    #
    # For the first, we store core.UNSET; for the second we pass None to our ACL
    # class and for the third and third we pass the PyACL through to our ACL.
    #
    # This is more complicated, tho', because the pywin32 GetSecurityDescriptorDacl/Sacl
    # function returns None in the first *and* second cases, making it impossible
    # to determine whether there is or isn't a DACL found. This means we can't
    # really distinguish a NULL ACL from a non-existent ACL. For simplicity, assume
    # it's there and pass None through to the ACL.
    #
    if not control & SD_CONTROL.DACL_PRESENT:
      dacl = core.UNSET
    else:
      dacl = sd.GetSecurityDescriptorDacl () if SECURITY_INFORMATION.DACL & options else core.UNSET
    if not control & SD_CONTROL.SACL_PRESENT:
      sacl = core.UNSET
    else:
      sacl = sd.GetSecurityDescriptorSacl () if SECURITY_INFORMATION.SACL & options else core.UNSET
    return cls (
      control,
      owner, group, dacl, sacl,
      inherit_handle,
      originating_object, originating_object_type
    )

  @classmethod
  def from_string (cls, sddl, options=core.UNSET):
    ur"""Constructs a :class:`Security` object from an SDDL string.
    Useful for round-tripping, since the :meth:`__str__` method produces
    an SDDL string.
    """
    if options is core.UNSET: options = cls.DEFAULT_OPTIONS
    
    return cls.from_security_descriptor (
      sd=wrapped (
        win32security.ConvertStringSecurityDescriptorToSecurityDescriptor,
        unicode (sddl),
        REVISION.SDDL_REVISION_1
      ), 
      options=options
    )

def security (obj=core.UNSET, obj_type=core.UNSET, options=core.UNSET):
  ur"""Return a :class:`Security` object representing the security attributes
  of a named object (eg a file, registry key) or a kernel object (eg a process,
  a pipe). With no parameters, an empty :class:`Security` object is returned which can then be
  set up with appropriate attributes and applied to other objects via its
  :meth:`to_object` method. :const:`None` and an existing :class:`Security` 
  object are passed through unchanged. A :const:`PySECURITY_DESCRIPTOR` is
  converted to the corresponding :class:`Security` object. A pywin32 :const:`PyHANDLE`,
  representing a kernel object finds the security attributes for that object.
  Finally, a string finds the security attributes for the object of that name.
  
  The most common use is to pass a filename. The :meth:`from_object` method
  assumes that an unqualified string represents a file. If it represents
  something else, you need to specify its type in the `obj_type` parameter::

    from winsys import security
    s = security.security ("c:/windows")
    s.dump ()
  
  :param obj: any of :const:`None`, a :class:`Security` object, a pywin32 :const:`PyHANDLE`,
              a pywin32 :const:`PySECURITY_DESCRIPTOR`, or a string
  :param obj_type: an :const:`SE_OBJECT_TYPE` [SE_OBJECT_TYPE.FILE_OBJECT]
  :param options: anything acccepted by :meth:`_options` [:const:`DEFAULT_OPTIONS`]
  :returns: a :class:`Security` object
  """
  if obj is None:
    return None
  elif obj is core.UNSET:
    return Security ()
  elif isinstance (obj, Security):
    return obj
  elif isinstance (obj, PyHANDLE):
    return Security.from_object (obj, obj_type, options=options)
  elif isinstance (obj, PySECURITY_DESCRIPTOR):
    return Security.from_security_descriptor (obj, options=options)
  else:
    return Security.from_object (unicode (obj), obj_type, options=options)

#
# Convenience functions
#
@contextlib.contextmanager
def impersonate (user, password=core.UNSET):
  ur"""Context-manager which impersonates a user with a password
  and then reverts to the current user::
  
    from __future__ import with_statement
    from winsys import security
    with security.impersonate ("Administrator", "password"):
      print security.me ()
      
  ..  note::
      A :class:`accounts.Principal` object is its own context manager
      although it's not then possible to pass in a password.
      
  :param user: any valid username
  :param password: username for that user; if not specified, user will be prompted
  """
  impersonation_token = token (principal (user).logon (password)).impersonate ()
  yield impersonation_token
  impersonation_token.unimpersonate ()

@contextlib.contextmanager
def change_privileges (enable_privs=[], disable_privs=[], _token=core.UNSET):
  ur"""Context manager which temporarily enables/disables privs within the 
  current token, reverting when done to the previous situation::
  
    from __future__ import with_statement
    from winsys import security, fs
    
    test = fs.file ("test")
    test.touch ()
    with security.change_privileges (["restore"]):
      with test.security () as s:
        print s.owner
        s.owner = security.principal ("Administrator")
        print s.owner
  
  :param enable_privs: list of privileges to enable; each priv is anything accepted by :func:`privilege`
  :param disable_privs: list of privileges to disable; each priv is anything accepted by :func:`privilege`
  :param _token: (internal) a token to use if not the current one
  :returns: yields re-privileged token object
  """
  if _token is core.UNSET:
    _token = token ()
  old_enabled_privs, old_disabled_privs = _token.change_privileges (enable_privs, disable_privs)
  yield _token
  _token.change_privileges (old_enabled_privs, old_disabled_privs)

def runas (user, password, command_line):
  with privilege (PRIVILEGE.TCB):
    with principal (user).impersonate (password, logon_type=LOGON.LOGON_INTERACTIVE) as hToken:
      token (hToken).dump ()
      hDuplicateToken = wrapped (
        win32security.DuplicateTokenEx,
        hToken,
        win32security.SecurityImpersonation,
        constants.GENERAL.MAXIMUM_ALLOWED,
        win32security.TokenPrimary,
        None
      )
      return wrapped (
        win32process.CreateProcessAsUser, 
        hDuplicateToken, 
        None, 
        command_line,
        None,
        None,
        1,
        0,
        None,
        None,
        win32process.STARTUPINFO ()
      )
