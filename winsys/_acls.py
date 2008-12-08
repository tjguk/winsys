# -*- coding: iso-8859-1 -*-
import os, sys

import win32security
import pywintypes
import winerror

from winsys import constants, core, utils, accounts, _aces
from winsys.exceptions import *

PyACL = pywintypes.ACLType

class x_acl (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_acl)

class ACL (core._WinSysObject):

  _ACE = _aces.ACE

  def __init__ (self, acl=None):
    core._WinSysObject.__init__ (self)
    if acl is None:
      self._list = None
    else:
      self._list = list (self._ACE.from_ace (acl.GetAce (index)) for index in range (acl.GetAceCount ()))

  def dumped (self, level=0):
    output = []
    for ace in self._list or []:
      output.append (ace.dumped (level))
    return utils.dumped (u"\n".join (output), level)

  def pyobject (self, *args, **kwargs):
    raise NotImplementedError

  def __iter__ (self):
    if self._list is None:
      raise x_value_not_set (u"No entry has been set for this ACL")
    else:
      return iter (sorted (self._list))

  def append (self, _ace):
    self._list.append (self._ACE.ace (_ace))

  def __getitem__ (self, index):
    return self._list[index]

  def __setitem__ (self, index, item):
    self._list[index] = self._ACE.ace (item)

  def __delitem__ (self, index):
    del self._list[index]

  def __len__ (self):
    return len (self._list or [])

  def __nonzero__ (self):
    return bool (self._list)

  def as_string (self):
    return repr (self._list)
  
  def __contains__ (self, a):
    return self._ACE.ace (a) in (self._list or [])

  @classmethod
  def from_list (cls, aces):
    acl = cls (wrapped (win32security.ACL))
    for a in aces:
      acl.append (cls._ACE.ace (a))
    return acl
  
class DACL (ACL):
  _ACE = _aces.DACE
  _ACE_MAP = {
    _aces.ACE_TYPE.ACCESS_ALLOWED : u"AddAccessAllowedAceEx",
    _aces.ACE_TYPE.ACCESS_DENIED : u"AddAccessDeniedAceEx",
  }

  def pyobject (self, include_inherited=False):
    if self._list is None:
      return None
    
    acl = wrapped (win32security.ACL)
    aces = sorted (a for a in self._list if not a.inherited or include_inherited)
    for ace in aces:
      adder_fn = self._ACE_MAP.get (ace.type)
      if adder_fn:
        adder = getattr (acl, adder_fn)
        adder (constants.REVISION.ACL_REVISION_DS, ace.flags, ace.access, ace.trustee.pyobject ())
      else:
        raise NotImplementedError, ace.type
    return acl
    
  @classmethod
  def public (cls):
    return cls.from_list ([(u"Everyone", u"F", u"ALLOW")])
    
  @classmethod
  def private (cls):
    return cls.from_list ([("", u"F", u"ALLOW")])

class SACL (ACL):
  _ACE = _aces.SACE
  _ACE_MAP = {
    _aces.ACE_TYPE.SYSTEM_AUDIT : u"AddAuditAccessAce",
  }
  
  def pyobject (self, include_inherited=False):
    if self._list is None:
      return None
    
    acl = wrapped (win32security.ACL)
    aces = sorted (a for a in self._list if not a.inherited or include_inherited)
    for ace in aces:
      adder_fn = self._ACE_MAP.get (ace.type)
      if adder_fn:
        adder = getattr (acl, adder_fn)
        adder (constants.REVISION.ACL_REVISION_DS, ace.access, ace.trustee.pyobject (), ace.audit_success, ace.audit_failure)
      else:
        raise NotImplementedError, ace.type
    return acl
    

def acl (acl, klass=core.UNSET):
  if klass is core.UNSET: klass = DACL
    
  if acl is None:
    return klass (None)
  elif type (acl) is PyACL:
    return klass (acl)
  elif isinstance (acl, ACL):
    return acl
  else:
    return klass.from_list (iter (acl))

def dacl (dacl):
  return acl (dacl, DACL)

def sacl (sacl):
  return acl (sacl, SACL)
