# -*- coding: iso-8859-1 -*-
import os, sys

import win32security
import pywintypes
import winerror

from winsys import constants, core, exc, utils, accounts
from winsys._security.core import REVISION
from winsys._security import _aces

__all__ = ['x_acl', 'ACL', 'DACL', 'SACL', 'acl', 'dacl', 'sacl']

PyACL = pywintypes.ACLType

class x_acl (exc.x_winsys):
  "Base for all ACL-related exceptions"
  
class x_value_not_set (x_acl):
  "Raised when iterating over an ACL which has not been set"

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_acl)

class ACL (core._WinSysObject):
  """An ACL maps the Windows security ACL concept, but behaves like
  a Python list. You can append to it, iterate over it, delete from
  it, check its length and test it for membership. A special case is
  made for the so-called NULL ACL. This is different from an empty
  ACL (which is effectively completely restrictive). A NULL ACL is
  completely unrestrictive. This is mapped by holding None and treating
  this specially where needed.
  
  DACL & SACL subclasses are defined to cope with the slightly different
  ways in which the structures are manipulated, but the core functionality
  is in this base class. This class need rarely be instantiated directly;
  normally it will be invoked by the Security class which is accessor
  properties for this purpose.
  """

  _ACE = _aces.ACE

  def __init__ (self, acl=None, inherited=True):
    core._WinSysObject.__init__ (self)
    if acl is None:
      self._list = None
    else:
      self._list = list (self._ACE.from_ace (acl.GetAce (index)) for index in range (acl.GetAceCount ()))
    self.inherited = inherited
    
    #
    # Used when inheritance is broken to keep
    # a copy of the inherited list.
    #
    self._original_list = []

  def dumped (self, level=0):
    output = []
    output.append (u"inherited: %s" % self.inherited)
    for ace in self._list or []:
      output.append (ace.dumped (level))
    return utils.dumped (u"\n".join (output), level)

  def pyobject (self, *args, **kwargs):
    raise NotImplementedError

  def __iter__ (self):
    if self._list is None:
      raise x_value_not_set (core.UNSET, "ACL.__iter__", u"No entry has been set for this ACL")
    else:
      return iter (sorted (self._list))

  def append (self, _ace):
    """Append an ACE to the ACL; it is assumed to be
    non-inherited as it's meaningless to add an inherited
    ace into an ACL.
    """
    ace = self._ACE.ace (_ace)
    ace.inherited = False
    self._list.append (ace)

  def extend (self, _aces):
    """Extend the ACL by adding ACE-type objects"""
    for _ace in _aces:
      ace = self._ACE.ace (_ace)
      ace.inherited = False
      self._list.append (ace)
  __iadd__ = extend

  def __getitem__ (self, index):
    return self._list[index]

  def __setitem__ (self, index, item):
    ace = self._ACE.ace (item)
    ace.inherited = False
    self._list[index] = ace

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
  def from_list (cls, aces, inherited=True):
    acl = cls (wrapped (win32security.ACL), inherited)
    for a in aces:
      acl.append (cls._ACE.ace (a))
    return acl
    
  def break_inheritance (self, copy_first):
    core.debug ("About to break_inheritance for %s with _list %s and copy_first %s", (self.__class__, self._list, copy_first))
    if self._list is not None:
      self._original_list = [a for a in self._list if a.inherited]
      if copy_first:
        core.debug ("Copy first")
        for ace in self._list:
          ace.inherited = False
      else:
        core.debug ("Not Copy first")
        self._list = [a for a in (self._list or []) if not a.inherited]
      core.debug ("After: _list", self._list)
    self.inherited = False

  def restore_inheritance (self, copy_back):
    if copy_back:
      if self._list is not None:
        self._list.extend (self._original_list)
    self.inherited = True

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
        adder (
          REVISION.ACL_REVISION_DS, 
          ace.flags, 
          ace.access, 
          ace.trustee.pyobject ()
        )
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
    _aces.ACE_TYPE.SYSTEM_AUDIT : u"AddAuditAccessAceEx",
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
        adder (
          REVISION.ACL_REVISION_DS, 
          ace.flags,
          ace.access, 
          ace.trustee.pyobject (), 
          ace.audit_success, 
          ace.audit_failure
        )
      else:
        raise NotImplementedError, ace.type
    return acl
    

def acl (acl, klass=core.UNSET, inherited=True):
  if klass is core.UNSET: klass = DACL
    
  if acl is None:
    return klass (None, inherited)
  elif type (acl) is PyACL:
    return klass (acl, inherited)
  elif isinstance (acl, ACL):
    return acl
  else:
    return klass.from_list (iter (acl), inherited)

def dacl (dacl, inherited=True):
  return acl (dacl, DACL, inherited)

def sacl (sacl, inherited=True):
  return acl (sacl, SACL, inherited)
