import os, sys
import operator

from nose.tools import *

from winsys import _aces, accounts
import win32security
import ntsecuritycon
import tempfile

everyone, _, _ = win32security.LookupAccountName (None, "Everyone")
me = accounts.me ()
administrators = accounts.principal ("Administrators")

filehandle = filename = None
def setup ():
  global filehandle, filename
  filehandle, filename = tempfile.mkstemp ()
  print filename
  dacl = win32security.ACL ()
  dacl.AddAccessAllowedAceEx (win32security.ACL_REVISION_DS, 0, ntsecuritycon.FILE_READ_DATA, everyone)
  win32security.SetNamedSecurityInfo (
    filename, win32security.SE_FILE_OBJECT, 
    win32security.DACL_SECURITY_INFORMATION, 
    None, None, dacl, None
  )
  
def teardown ():
  os.close (filehandle)
  os.unlink (filename)

def test_ace_ace ():
  ace = _aces.ACE (everyone, "F", "ALLOW")
  assert _aces.ace (ace) is ace

def test_ace_tuple1 ():
  ace1 = _aces.ace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE))
  assert ace1.type == win32security.ACCESS_ALLOWED_ACE_TYPE
  assert ace1.is_allowed == True
  assert ace1._trustee.pyobject () == everyone
  assert ace1._access_mask == ntsecuritycon.GENERIC_ALL
  assert ace1._flags == _aces.ACE.FLAGS
  assert ace1.object_type is None
  assert ace1.inherited_object_type is None
  
def test_ace_tuple2 ():
  ace2 = _aces.ace ((accounts.principal ("Everyone"), "F", "ALLOW"))
  assert ace2.type == win32security.ACCESS_ALLOWED_ACE_TYPE
  assert ace2.is_allowed == True
  assert ace2._trustee.pyobject () == everyone
  assert ace2._access_mask == ntsecuritycon.GENERIC_ALL
  assert ace2._flags == _aces.ACE.FLAGS
  assert ace2.object_type is None
  assert ace2.inherited_object_type is None

@raises (_aces.x_ace)
def test_ace_invalid ():
  _aces.ace (None)

def test_ace_eq ():
  assert \
    _aces.ace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) == \
    _aces.ace ((accounts.principal ("Everyone"), "F", "ALLOW"))

def test_ace_ne_trustee ():
   assert \
    _aces.ace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.ace ((accounts.principal ("Administrators"), "F", "ALLOW"))

def test_ace_ne_access ():
   assert \
    _aces.ace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.ace ((accounts.principal ("Everyone"), "R", "ALLOW"))

def test_ace_ne_type ():
   assert \
    _aces.ace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.ace ((accounts.principal ("Everyone"), "R", "DENY"))

def test_ace_lt ():
  assert _aces.ace (("Everyone", "R", "DENY")) < _aces.ace (("Everyone", "R", "ALLOW"))

def test_ace_as_string ():
  _aces.ace (("Everyone", "R", "ALLOW")).as_string ()

#
# INHERITED_ACE
#
def test_ace_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags |= win32security.INHERITED_ACE
  assert ace.inherited

def test_ace_not_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  assert not ace.inherited

def test_ace_set_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  assert not ace.inherited
  ace.inherited = True
  assert ace._flags & win32security.INHERITED_ACE

def test_ace_reset_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags |= win32security.INHERITED_ACE
  assert ace.inherited
  ace.inherited = False
  assert not ace._flags & win32security.INHERITED_ACE

#
# CONTAINER_INHERIT_ACE
#
def test_ace_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags |= win32security.CONTAINER_INHERIT_ACE
  assert ace.containers_inherit

def test_ace_not_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.CONTAINER_INHERIT_ACE
  assert not ace.containers_inherit

def test_ace_set_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  ace._flags &= ~win32security.CONTAINER_INHERIT_ACE
  assert not ace.containers_inherit
  ace.containers_inherit = True
  assert ace._flags & win32security.CONTAINER_INHERIT_ACE

def test_ace_reset_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  ace._flags |= win32security.CONTAINER_INHERIT_ACE
  assert ace.containers_inherit
  ace.containers_inherit = False
  assert not ace._flags & win32security.CONTAINER_INHERIT_ACE

#
# OBJECTS_INHERIT_aCE
#
def test_ace_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags |= win32security.OBJECT_INHERIT_ACE
  assert ace.objects_inherit

def test_ace_not_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.OBJECT_INHERIT_ACE
  assert not ace.objects_inherit

def test_ace_set_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  ace._flags &= ~win32security.OBJECT_INHERIT_ACE
  assert not ace.objects_inherit
  ace.objects_inherit = True
  assert ace._flags & win32security.OBJECT_INHERIT_ACE

def test_ace_reset_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace._flags &= ~win32security.INHERITED_ACE
  ace._flags |= win32security.OBJECT_INHERIT_ACE
  assert ace.objects_inherit
  ace.objects_inherit = False
  assert not ace._flags & win32security.OBJECT_INHERIT_ACE

#
# access
#
def test_ace_access_int ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  assert ace._access_mask == ntsecuritycon.GENERIC_ALL
  ace.access = ntsecuritycon.GENERIC_READ
  assert ace._access_mask == ntsecuritycon.GENERIC_READ
  
def test_ace_access_string ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  assert ace._access_mask == ntsecuritycon.GENERIC_ALL
  ace.access = "W"
  assert ace._access_mask == ntsecuritycon.GENERIC_WRITE

#
# trustee
#
def test_ace_trustee_principal ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  assert ace._trustee == everyone
  ace.trustee = me
  assert ace._trustee == me
  
def test_ace_trustee_string ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  assert ace._trustee == everyone
  ace.trustee = "Administrators"
  assert ace._trustee == administrators

#
# ACE constructors
#
def test_ace_from_ace ():
  sd = win32security.GetNamedSecurityInfo (
    filename, win32security.SE_FILE_OBJECT, 
    win32security.DACL_SECURITY_INFORMATION
  )
  dacl = sd.GetSecurityDescriptorDacl ()
  raw_ace = dacl.GetAce (0)
  ace = _aces.ACE.from_ace (raw_ace)
  assert ace.trustee.pyobject () == everyone
  assert ace.access == ntsecuritycon.FILE_READ_DATA
  assert ace.type == win32security.ACCESS_ALLOWED_ACE_TYPE

##
## TODO: Add tests for object aces, sacl vs dacl aces
##

#
# Check that you can't change any of the attributes of an inherited ACE
#
@raises (_aces.x_access_denied)
def test_ace_set_containers_inherit_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).containers_inherit = True

@raises (_aces.x_access_denied)
def test_ace_set_objects_inherit_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).objects_inherit = True

@raises (_aces.x_access_denied)
def test_ace_set_access_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).access = 0

@raises (_aces.x_access_denied)
def test_ace_set_trustee_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).trustee = ""

def test_ace_access_int ():
  assert _aces.ACE._access (1) == 1
  
def test_ace_access_string ():
  for k, v in _aces.ACE.ACCESS.items ():
    assert _aces.ACE._access (k) == v
  assert _aces.ACE._access ("".join (_aces.ACE.ACCESS.keys ())) == reduce (operator.or_, _aces.ACE.ACCESS.values ())

@raises (_aces.x_unknown_value)
def test_ace_access_invalid ():
  assert "*" not in _aces.ACE.ACCESS
  _aces.ACE._access ("*")

def test_ace_type_int ():
  assert _aces.ACE._type (1) == 1

def test_ace_type_string ():
  for k, v in _aces.ACE.TYPES.items ():
    assert _aces.ACE._type (k) == v

@raises (_aces.x_unknown_value)
def test_ace_type_invalid ():
  assert "*" not in _aces.ACE.TYPES
  _aces.ACE._type ("*")

def test_ace_as_tuple ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)
  assert ace.as_tuple () == (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)
