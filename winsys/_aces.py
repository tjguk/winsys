# -*- coding: iso-8859-1 -*-
import os, sys
import operator

from winsys import core, utils, accounts
from winsys.constants import *
from winsys.exceptions import *

class x_ace (x_winsys):
  pass

class ACE (core._WinSysObject):

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
    core._WinSysObject.__init__ (self)
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
    return bool (self._flags & ACE_FLAG.CONTAINER_INHERIT)
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
      if name in ACE_TYPE.names (u"ACCESS_*"):
        _class = DACE
      else:
        _class = SACE

    return _class (accounts.principal (sid), mask, type, flags, object_type, inherited_object_type)

  @classmethod
  def _access (cls, access):
    try:
      return int (access)
    except (ValueError, TypeError):
      return reduce (operator.or_, (cls.ACCESS[a] for a in access.upper ()), 0)
        
  @classmethod
  def _type (cls, type):
    try:
      return int (type)
    except (ValueError, TypeError):
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

#
# Friendly constructors
#
def ace (ace):
  if ace is None:
    return None
  elif issubclass (ace.__class__, ACE):
    return ace
  else:
    try:
      return ACE.from_tuple (ace)
    except ValueError:
      raise x_ace ("ACE must be None, an existing ACE or a 3-tuple of (trustee, access, type)", "ace", 0)
