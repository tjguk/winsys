# -*- coding: iso-8859-1 -*-
import os, sys

import win32security
import pywintypes
import winerror

from winsys import core, utils, accounts, _aces
from winsys.constants import *
from winsys.exceptions import *

PyACL = pywintypes.ACLType

class x_acl (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_acl)

class ACL (core._WinSysObject):

  _ACE = _aces.ACE
  _ACE_MAP = {
    ACE_TYPE.ACCESS_ALLOWED : u"AddAccessAllowedAceEx",
    ACE_TYPE.ACCESS_DENIED : u"AddAccessDeniedAceEx"
  }

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

  def __iter__ (self):
    if self._list is None:
      raise x_value_not_set (u"No entry has been set for this ACL")
    else:
      return iter (sorted (self._list))

  def append (self, _ace):
    self._list.append (_aces.ace (_ace))

  def __getitem__ (self, index):
    return self._list[index]

  def __setitem__ (self, index, item):
    self._list[index] = _aces.ace (item)

  def __delitem__ (self, index):
    del self._list[index]

  def __len__ (self):
    return len (self._list or [])

  def __nonzero__ (self):
    return bool (self._list)

  def as_string (self):
    return repr (self._list)
  
  def __contains__ (self, a):
    return _aces.ace (a) in (self._list or [])

  def pyobject (self, include_inherited=False):
    if self._list is None:
      return None
    
    acl = wrapped (win32security.ACL)
    aces = sorted (a for a in self._list if not a.inherited or include_inherited)
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
      acl.append (_aces.ace (a))
    return acl
  
  @classmethod
  def public (cls):
    return cls.from_list ([(u"Everyone", u"F", u"ALLOW")])
    
  @classmethod
  def private (cls):
    return cls.from_list ([("", u"F", u"ALLOW")])

class DACL (ACL):
  _ACE = _aces.DACE

class SACL (ACL):
  _ACE = _aces.SACE

def acl (acl):
  if acl is None:
    return ACL (None)
  elif type (acl) is PyACL:
    return ACL (acl)
  elif issubclass (acl.__class__, ACL):
    return acl
  else:
    return ACL.from_list (iter (acl))
