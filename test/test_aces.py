import os, sys
import operator

from nose.tools import *
import utils

from winsys import core, _aces, accounts
import win32security
import ntsecuritycon
import tempfile

everyone, _, _ = win32security.LookupAccountName (None, "Everyone")
me = accounts.me ()
administrators = accounts.principal ("Administrators")

filehandle = filename = None
def setup ():
  utils.change_priv (win32security.SE_SECURITY_NAME, True)
  global filehandle, filename
  filehandle, filename = tempfile.mkstemp ()
  print filename
  dacl = win32security.ACL ()
  dacl.AddAccessAllowedAceEx (win32security.ACL_REVISION_DS, 0, ntsecuritycon.FILE_READ_DATA, everyone)
  sacl = win32security.ACL ()
  sacl.AddAuditAccessAce (win32security.ACL_REVISION_DS, ntsecuritycon.FILE_READ_DATA, everyone, 1, 1)
  win32security.SetNamedSecurityInfo (
    filename, win32security.SE_FILE_OBJECT, 
    win32security.DACL_SECURITY_INFORMATION | win32security.SACL_SECURITY_INFORMATION, 
    None, None, dacl, sacl
  )
  
def teardown ():
  os.close (filehandle)
  os.unlink (filename)
  utils.change_priv (win32security.SE_SECURITY_NAME, False)

def test_dace_dace ():
  dace = _aces.DACE (everyone, "F", "ALLOW")
  assert _aces.dace (dace) is dace

def test_sace_sace ():
  sace = _aces.SACE (everyone, "F", "SUCCESS")
  assert _aces.sace (sace) is sace

def test_ace_dace ():
  dace = _aces.DACE (everyone, "F", "ALLOW")
  assert _aces.ace (dace) is dace

def test_ace_sace ():
  sace = _aces.SACE (everyone, "F", "FAILURE")
  assert _aces.ace (sace) is sace

def test_dace_tuple1 ():
  dace1 = _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE))
  assert dace1.type == win32security.ACCESS_ALLOWED_ACE_TYPE
  assert dace1.is_allowed == True
  assert dace1._trustee.pyobject () == everyone
  assert dace1._access_mask == ntsecuritycon.GENERIC_ALL
  assert dace1.flags == _aces.ACE.FLAGS
  assert dace1.object_type is core.UNSET
  assert dace1.inherited_object_type is core.UNSET
  
def test_dace_tuple2 ():
  dace2 = _aces.dace ((accounts.principal ("Everyone"), "F", "ALLOW"))
  assert dace2.type == win32security.ACCESS_ALLOWED_ACE_TYPE
  assert dace2.is_allowed == True
  assert dace2._trustee.pyobject () == everyone
  assert dace2._access_mask == ntsecuritycon.GENERIC_ALL
  assert dace2.flags == _aces.ACE.FLAGS
  assert dace2.object_type is core.UNSET
  assert dace2.inherited_object_type is core.UNSET

@raises (_aces.x_ace)
def test_dace_invalid ():
  _aces.dace (None)

def test_dace_eq ():
  assert \
    _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) == \
    _aces.dace ((accounts.principal ("Everyone"), "F", "ALLOW"))

def test_dace_ne_trustee ():
   assert \
    _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.dace ((accounts.principal ("Administrators"), "F", "ALLOW"))

def test_dace_ne_access ():
   assert \
    _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.dace ((accounts.principal ("Everyone"), "R", "ALLOW"))

def test_dace_ne_type ():
   assert \
    _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
    _aces.dace ((accounts.principal ("Everyone"), "R", "DENY"))

def test_dace_lt ():
  assert _aces.dace (("Everyone", "R", "DENY")) < _aces.dace (("Everyone", "R", "ALLOW"))

def test_dace_as_string ():
  _aces.dace (("Everyone", "R", "ALLOW")).as_string ()

#
# SACE tests
#
def test_sace_tuple1 ():
  sace1 = _aces.sace ((everyone, ntsecuritycon.GENERIC_ALL, (1, 0)))
  assert sace1.type == win32security.SYSTEM_AUDIT_ACE_TYPE
  assert sace1.audit_success
  assert not sace1.audit_failure
  assert sace1._trustee.pyobject () == everyone
  assert sace1._access_mask == ntsecuritycon.GENERIC_ALL
  assert sace1.flags == _aces.ACE.FLAGS
  assert sace1.object_type is core.UNSET
  assert sace1.inherited_object_type is core.UNSET
  
def test_sace_tuple2 ():
  sace1 = _aces.sace ((accounts.principal ("Everyone"), "F", "FAILURE"))
  assert sace1.type == win32security.SYSTEM_AUDIT_ACE_TYPE
  assert not sace1.audit_success
  assert sace1.audit_failure
  assert sace1._trustee.pyobject () == everyone
  assert sace1._access_mask == ntsecuritycon.GENERIC_ALL
  assert sace1.flags == _aces.ACE.FLAGS
  assert sace1.object_type is core.UNSET
  assert sace1.inherited_object_type is core.UNSET

@raises (_aces.x_ace)
def test_sace_invalid ():
  _aces.sace (None)

def test_sace_eq ():
  assert \
    _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 1))) == \
    _aces.sace ((accounts.principal ("Everyone"), "F", "ALL"))

def test_sace_ne_trustee ():
   assert \
    _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 1))) != \
    _aces.sace ((accounts.principal ("Administrators"), "F", "ALL"))

def test_sace_ne_access ():
   assert \
    _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 0))) != \
    _aces.sace ((accounts.principal ("Everyone"), "R", (1, 0)))

def test_sace_ne_type ():
   assert \
    _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 0))) != \
    _aces.sace ((accounts.principal ("Everyone"), "R", "FAILURE"))

def test_sace_lt ():
  assert _aces.sace (("Everyone", "R", (1, 1))) < _aces.sace (("Everyone", "R", (0, 1)))

def test_sace_as_string ():
  _aces.sace (("Everyone", "R", "ALL")).as_string ()


#
# INHERITED_ACE
#
def test_ace_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags |= win32security.INHERITED_ACE
  assert ace.inherited

def test_ace_not_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  assert not ace.inherited

def test_ace_set_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  assert not ace.inherited
  ace.inherited = True
  assert ace.flags & win32security.INHERITED_ACE

def test_ace_reset_inherited ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags |= win32security.INHERITED_ACE
  assert ace.inherited
  ace.inherited = False
  assert not ace.flags & win32security.INHERITED_ACE

#
# CONTAINER_INHERIT_ACE
#
def test_ace_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags |= win32security.CONTAINER_INHERIT_ACE
  assert ace.containers_inherit

def test_ace_not_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.CONTAINER_INHERIT_ACE
  assert not ace.containers_inherit

def test_ace_set_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  ace.flags &= ~win32security.CONTAINER_INHERIT_ACE
  assert not ace.containers_inherit
  ace.containers_inherit = True
  assert ace.flags & win32security.CONTAINER_INHERIT_ACE

def test_ace_reset_containers_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  ace.flags |= win32security.CONTAINER_INHERIT_ACE
  assert ace.containers_inherit
  ace.containers_inherit = False
  assert not ace.flags & win32security.CONTAINER_INHERIT_ACE

#
# OBJECTS_INHERIT_aCE
#
def test_ace_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags |= win32security.OBJECT_INHERIT_ACE
  assert ace.objects_inherit

def test_ace_not_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.OBJECT_INHERIT_ACE
  assert not ace.objects_inherit

def test_ace_set_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  ace.flags &= ~win32security.OBJECT_INHERIT_ACE
  assert not ace.objects_inherit
  ace.objects_inherit = True
  assert ace.flags & win32security.OBJECT_INHERIT_ACE

def test_ace_reset_objects_inherit ():
  ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
  ace.flags &= ~win32security.INHERITED_ACE
  ace.flags |= win32security.OBJECT_INHERIT_ACE
  assert ace.objects_inherit
  ace.objects_inherit = False
  assert not ace.flags & win32security.OBJECT_INHERIT_ACE

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
def test_ace_from_ace_dace ():
  sd = win32security.GetNamedSecurityInfo (
    filename, win32security.SE_FILE_OBJECT, 
    win32security.DACL_SECURITY_INFORMATION
  )
  dacl = sd.GetSecurityDescriptorDacl ()
  raw_ace = dacl.GetAce (0)
  ace = _aces.ACE.from_ace (raw_ace)
  assert isinstance (ace, _aces.DACE)
  assert ace.trustee.pyobject () == everyone
  assert ace.access == ntsecuritycon.FILE_READ_DATA
  assert ace.type == win32security.ACCESS_ALLOWED_ACE_TYPE

def test_ace_from_ace_sace ():
  sd = win32security.GetNamedSecurityInfo (
    filename, win32security.SE_FILE_OBJECT, 
    win32security.SACL_SECURITY_INFORMATION
  )
  sacl = sd.GetSecurityDescriptorSacl ()
  raw_ace = sacl.GetAce (0)
  ace = _aces.ACE.from_ace (raw_ace)
  assert isinstance (ace, _aces.SACE)
  assert ace.trustee.pyobject () == everyone
  assert ace.access == ntsecuritycon.FILE_READ_DATA
  assert ace.type == win32security.SYSTEM_AUDIT_ACE_TYPE

##
## TODO: Add tests for object aces, sacl vs dacl aces
##

#
# Check that you can't change any of the attributes of an inherited ACE
#
@raises (_aces.exc.x_access_denied)
def test_ace_set_containers_inherit_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).containers_inherit = True

@raises (_aces.exc.x_access_denied)
def test_ace_set_objects_inherit_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).objects_inherit = True

@raises (_aces.exc.x_access_denied)
def test_ace_set_access_inherited ():
  _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).access = 0

@raises (_aces.exc.x_access_denied)
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

def test_dace_type_int ():
  assert _aces.DACE._type (1) == 1

def test_dace_type_string ():
  for k, v in _aces.DACE.TYPES.items ():
    assert _aces.DACE._type (k) == v

@raises (_aces.x_unknown_value)
def test_dace_type_invalid ():
  assert "*" not in _aces.DACE.TYPES
  _aces.DACE._type ("*")

def test_dace_as_tuple ():
  dace = _aces.DACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)
  assert dace.as_tuple () == (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)

if __name__ == '__main__':
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
