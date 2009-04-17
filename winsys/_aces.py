# -*- coding: iso-8859-1 -*-
import os, sys
import operator

import win32security
from winsys import core, exc, utils, accounts, constants

__all__ = ['x_ace', 'x_unknown_value', 'ACE_FLAG', 'ACE_TYPE', 'DACE_TYPE', 'SACE_TYPE', 'ACE', 'DACE', 'SACE', 'dace', 'sace', 'ace']

class x_ace (exc.x_winsys):
  pass

class x_unknown_value (x_ace):
  pass

ACE_FLAG = constants.Constants.from_list ([
  u"CONTAINER_INHERIT_ACE", 
  u"INHERIT_ONLY_ACE", 
  u"INHERITED_ACE", 
  u"NO_PROPAGATE_INHERIT_ACE", 
  u"OBJECT_INHERIT_ACE",
  u"FAILED_ACCESS_ACE_FLAG",
  u"SUCCESSFUL_ACCESS_ACE_FLAG"
], pattern=u"*_ACE", namespace=win32security)
ACE_TYPE = constants.Constants.from_pattern (u"*_ACE_TYPE", namespace=win32security)
DACE_TYPE = constants.Constants.from_pattern (u"ACCESS_*_ACE_TYPE", namespace=win32security)
SACE_TYPE = constants.Constants.from_pattern (u"SYSTEM_*_ACE_TYPE", namespace=win32security)

class ACE (core._WinSysObject):

  ACCESS = {
    u"R" : constants.GENERIC_ACCESS.READ,
    u"W" : constants.GENERIC_ACCESS.WRITE,
    u"X" : constants.GENERIC_ACCESS.EXECUTE,
    u"C" : constants.GENERIC_ACCESS.READ | constants.GENERIC_ACCESS.WRITE | constants.GENERIC_ACCESS.EXECUTE,
    u"F" : constants.GENERIC_ACCESS.ALL
  }
  FLAGS = ACE_FLAG.OBJECT_INHERIT | ACE_FLAG.CONTAINER_INHERIT
  
  def __init__ (self, trustee, access, type, flags=core.UNSET, object_type=core.UNSET, inherited_object_type=core.UNSET):
    u"""Construct a new ACE

    @param trustee "domain \ user" or Principal instance representing the security principal
    @param access Bitmask or "RWXCF"
    @param type "ALLOW" or "DENY" or number representing one of the *_ACE_TYPE constants
    @param flags Bitmask or Set of strings or numbers representing the AceFlags constants
    """
    core._WinSysObject.__init__ (self)
    if flags is core.UNSET: flags = self.FLAGS
    
    self.type = type
    self._trustee = trustee
    self._access_mask = access
    self.flags = flags
    self.object_type = object_type
    self.inherited_object_type = inherited_object_type
    
  def _id (self):
    return (self.trustee, self.access, self.type)

  def as_string (self):
    type = ACE_TYPE.name_from_value (self.type)
    flags = " | ".join (ACE_FLAG.names_from_value (self.flags))
    access = utils.mask_as_string (self.access)
    return u"%s %s %s %s" % (self.trustee, access, flags, type)

  def dumped (self, level):
    output = []
    output.append (u"trustee: %s" % self.trustee)
    output.append (u"access: %s" % utils.mask_as_string (self.access))
    output.append (u"type: %s" % ACE_TYPE.name_from_value (self.type))
    if self.flags:
      output.append (u"flags:\n%s" % utils.dumped_flags (self.flags, ACE_FLAG, level))
    return utils.dumped (u"\n".join (output), level)
  
  def _get_inherited (self):
    return bool (self.flags & ACE_FLAG.INHERITED)
  def _set_inherited (self, switch):
    if switch:
      self.flags |= ACE_FLAG.INHERITED
    else:
      self.flags &= ~ACE_FLAG.INHERITED
  inherited = property (_get_inherited, _set_inherited)
  
  def _get_containers_inherit (self):
    return bool (self.flags & ACE_FLAG.CONTAINER_INHERIT)
  def _set_containers_inherit (self, switch):
    if self.inherited:
      raise exc.x_access_denied (core.UNSET, u"ACE._get_containers_inherit", u"Cannot change an inherited ACE")
    if switch:
      self.flags |= ACE_FLAG.CONTAINER_INHERIT
    else:
      self.flags &= ~ACE_FLAG.CONTAINER_INHERIT
  containers_inherit = property (_get_containers_inherit, _set_containers_inherit)
  
  def _get_objects_inherit (self):
    return bool (self.flags & ACE_FLAG.OBJECT_INHERIT)
  def _set_objects_inherit (self, switch):
    if self.inherited:
      raise exc.x_access_denied (core.UNSET, u"ACE._get_objects_inherit", u"Cannot change an inherited ACE")
    if switch:
      self.flags |= ACE_FLAG.OBJECT_INHERIT
    else:
      self.flags &= ~ACE_FLAG.OBJECT_INHERIT
  objects_inherit = property (_get_objects_inherit, _set_objects_inherit)
  
  def _get_access (self):
    return self._access_mask
  def _set_access (self, access):
    if self.inherited:
      raise exc.x_access_denied (core.UNSET, u"ACE._set_access", u"Cannot change an inherited ACE")
    self._access_mask = self._access (access)
  access = property (_get_access, _set_access)
  
  def _get_trustee (self):
    return self._trustee
  def _set_trustee (self, trustee):
    if self.inherited:
      raise exc.x_access_denied (core.UNSET, u"ACE._get_trustee", u"Cannot change an inherited ACE")
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
      try:
        return reduce (operator.or_, (cls.ACCESS[a] for a in access.upper ()), 0)
      except KeyError:
        raise x_unknown_value (core.UNSET, u"ACE._access", "%s is not a valid access string" % access)
        
class DACE (ACE):
  
  TYPES = {
    u"ALLOW" : ACE_TYPE.ACCESS_ALLOWED,
    u"DENY" : ACE_TYPE.ACCESS_DENIED,
  }

  def __init__ (
    self, 
    trustee, access, type, 
    flags=core.UNSET, 
    object_type=core.UNSET, inherited_object_type=core.UNSET
  ):
    ACE.__init__ (self, trustee, access, type, flags, object_type, inherited_object_type)
    self.is_allowed = type in (ACE_TYPE.ACCESS_ALLOWED, ACE_TYPE.ACCESS_ALLOWED_OBJECT)

  def as_tuple (self):
    return self.trustee, self.access, self.type, self.flags

  @classmethod
  def ace (cls, ace):
    return dace (ace)

  @classmethod
  def from_tuple (cls, ace_info):
    (trustee, access, allow_or_deny) = ace_info
    return cls (accounts.principal (trustee), cls._access (access), cls._type (allow_or_deny))

  @classmethod
  def _type (cls, type):
    try:
      return int (type)
    except (ValueError, TypeError):
      try:
        return cls.TYPES[type.upper ()]
    except KeyError:
      raise x_unknown_value (core.UNSET, "ACE._type", "%s is not a valid type string" % type)
  
  def __eq__ (self, other):
    other = self.ace (other)
    return (self.trustee, self.access, self.type) == (other.trustee, other.access, other.type)
    
  def __lt__ (self, other):
    u"""Deny comes first, then what?"""
    other = self.ace (other)
    return (self.is_allowed < other.is_allowed)
    
class SACE (ACE):
  
  AUDIT_WHAT = {
    "SUCCESS" : (1, 0),
    "FAILURE" : (0, 1),
    "ALL" : (1, 1),
  }

  def __init__ (
    self,
    trustee, access, type, 
    flags=core.UNSET,
    audit_success=core.UNSET, audit_failure=core.UNSET, 
    object_type=core.UNSET, inherited_object_type=core.UNSET
  ):
    ACE.__init__ (self, trustee, access, type, flags, object_type, inherited_object_type)
    self.audit_success = audit_success or (ACE_FLAG.SUCCESSFUL_ACCESS & self.flags)
    self.audit_failure = audit_failure or (ACE_FLAG.FAILED_ACCESS & self.flags)

  @classmethod
  def ace (cls, ace):
    return sace (ace)
  
  @classmethod
  def from_tuple (cls, ace_info):
    (trustee, access, audit_what) = ace_info
    audit_success, audit_failure = cls._audit_what (audit_what)
    return cls (
      trustee=accounts.principal (trustee), 
      access=cls._access (access), 
      type=ACE_TYPE.SYSTEM_AUDIT, 
      audit_success=audit_success, 
      audit_failure=audit_failure
    )

  @classmethod
  def _audit_what (cls, audit_what):
    try:
      audit_success, audit_failure = [int (i) for i in audit_what]
    except (ValueError, TypeError):
      audit_success, audit_failure = cls.AUDIT_WHAT[audit_what.upper ()]
    return audit_success, audit_failure
  
  def as_tuple (self):
    return self.trustee, self.access, self.type, self.flags, (self.audit_success, self.audit_failure)

  def __eq__ (self, other):
    other = self.ace (other)
    return self.as_tuple () == other.as_tuple ()
    
  def __lt__ (self, other):
    """Failure before success"""
    other = self.ace (other)
    return self.audit_failure > other.audit_failure or self.audit_success > other.audit_success

#
# Friendly constructors
#
def dace (dace):
  """Attempt to return a DACE either from an existing DACE
  or from a tuple of trustee, access, type. Each element will
  be passed to its corresponding factory function so trustee may be
  anything which a principal () will accept; access may be an
  int flagset or one of the ACCESS strings; type is one of the
  DACE_TYPE flags or one of the TYPES strings.
  """
  try:
    if isinstance (dace, DACE):
      return dace
    else:
      return DACE.from_tuple (dace)
  except (ValueError, TypeError):
    raise x_ace (core.UNSET, "dace", "DACE must be an existing DACE or a 3-tuple of (trustee, access, type)")

def sace (sace):
  """Attempt to return a SACE either from an existing SACE
  or from a tuple of trustee, access, type. Each element will
  be passed to its corresponding factory function so trustee may be
  anything which a principal () will accept; access may be an
  int flagset or one of the ACCESS strings; audit_what is either a
  2-tuple of (audit_success, audit_failure) booleans or one of the
  AUDIT_WHAT strings.
  """
  try:
    if isinstance (sace, SACE):
      return sace
    else:
      return SACE.from_tuple (sace)
  except (ValueError, TypeError):
    raise x_ace (core.UNSET, "sace", "SACE must be an existing SACE or a 4-tuple of (trustee, access, audit_what)")

def ace (ace):
  """Attempt to return a SACE / DACE depending on the structure passed
  in. An existing ACE subtype will be passed straight through while if
  a tuple is passed through, the last element is used as a distinguisher.
  """
  try:
    if isinstance (ace, ACE):
      return ace
    else:
      trustee, access, data = ace
      if data in DACE.TYPES.keys () + DACE.TYPES.values ():
        return DACE.from_tuple (ace)
      elif data in SACE.AUDIT_WHAT.keys () + SACE.AUDIT_WHAT.values ():
        return SACE.from_tuple (ace)
      else:
        raise TypeError
  except (ValueError, TypeError):
    raise x_ace (core.UNSET, "ace", "ACE must be an existing DACE/SACE or a 3-tuple which can be passed to dace or sace")
