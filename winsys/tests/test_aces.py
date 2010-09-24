import os, sys
import functools
import operator

import win32security
import ntsecuritycon
import tempfile
import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0

from winsys.tests import utils

from winsys import core, accounts
from winsys._security import _aces

everyone, _, _ = win32security.LookupAccountName (None, "Everyone")
me = accounts.me ()
administrators = accounts.principal ("Administrators")

class TestAces (unittest.TestCase):

  def setUp (self):
    utils.change_priv (win32security.SE_SECURITY_NAME, True)
    self.filehandle, self.filename = tempfile.mkstemp ()
    dacl = win32security.ACL ()
    dacl.AddAccessAllowedAceEx (win32security.ACL_REVISION_DS, 0, ntsecuritycon.FILE_READ_DATA, everyone)
    sacl = win32security.ACL ()
    sacl.AddAuditAccessAce (win32security.ACL_REVISION_DS, ntsecuritycon.FILE_READ_DATA, everyone, 1, 1)
    win32security.SetNamedSecurityInfo (
      self.filename, win32security.SE_FILE_OBJECT,
      win32security.DACL_SECURITY_INFORMATION | win32security.SACL_SECURITY_INFORMATION,
      None, None, dacl, sacl
    )

  def tearDown (self):
    os.close (self.filehandle)
    os.unlink (self.filename)
    utils.change_priv (win32security.SE_SECURITY_NAME, False)

  def test_dace_dace (self):
    dace = _aces.DACE (everyone, "F", "ALLOW")
    assert _aces.dace (dace) is dace

  def test_sace_sace (self):
    sace = _aces.SACE (everyone, "F", "SUCCESS")
    assert _aces.sace (sace) is sace

  def test_ace_dace (self):
    dace = _aces.DACE (everyone, "F", "ALLOW")
    assert _aces.ace (dace) is dace

  def test_ace_sace (self):
    sace = _aces.SACE (everyone, "F", "FAILURE")
    assert _aces.ace (sace) is sace

  def test_dace_tuple1 (self):
    dace1 = _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE))
    assert dace1.type == win32security.ACCESS_ALLOWED_ACE_TYPE
    assert dace1.is_allowed == True
    assert dace1._trustee.pyobject () == everyone
    assert dace1._access_mask == ntsecuritycon.GENERIC_ALL
    assert dace1.flags == _aces.ACE.FLAGS
    assert dace1.object_type is core.UNSET
    assert dace1.inherited_object_type is core.UNSET

  def test_dace_tuple2 (self):
    dace2 = _aces.dace ((accounts.principal ("Everyone"), "F", "ALLOW"))
    assert dace2.type == win32security.ACCESS_ALLOWED_ACE_TYPE
    assert dace2.is_allowed == True
    assert dace2._trustee.pyobject () == everyone
    assert dace2._access_mask == ntsecuritycon.GENERIC_ALL
    assert dace2.flags == _aces.ACE.FLAGS
    assert dace2.object_type is core.UNSET
    assert dace2.inherited_object_type is core.UNSET

  def test_dace_invalid (self):
    with self.assertRaises (_aces.x_ace):
      _aces.dace (None)

  def test_dace_eq (self):
    assert \
      _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) == \
      _aces.dace ((accounts.principal ("Everyone"), "F", "ALLOW"))

  def test_dace_ne_trustee (self):
     assert \
      _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
      _aces.dace ((accounts.principal ("Administrators"), "F", "ALLOW"))

  def test_dace_ne_access (self):
     assert \
      _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
      _aces.dace ((accounts.principal ("Everyone"), "R", "ALLOW"))

  def test_dace_ne_type (self):
     assert \
      _aces.dace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)) != \
      _aces.dace ((accounts.principal ("Everyone"), "R", "DENY"))

  def test_dace_lt (self):
    assert _aces.dace (("Everyone", "R", "DENY")) < _aces.dace (("Everyone", "R", "ALLOW"))

  def test_dace_as_string (self):
    _aces.dace (("Everyone", "R", "ALLOW")).as_string ()

  #
  # SACE tests
  #
  def test_sace_tuple1 (self):
    sace1 = _aces.sace ((everyone, ntsecuritycon.GENERIC_ALL, (1, 0)))
    assert sace1.type == win32security.SYSTEM_AUDIT_ACE_TYPE
    assert sace1.audit_success
    assert not sace1.audit_failure
    assert sace1._trustee.pyobject () == everyone
    assert sace1._access_mask == ntsecuritycon.GENERIC_ALL
    assert sace1.flags == _aces.ACE.FLAGS
    assert sace1.object_type is core.UNSET
    assert sace1.inherited_object_type is core.UNSET

  def test_sace_tuple2 (self):
    sace1 = _aces.sace ((accounts.principal ("Everyone"), "F", "FAILURE"))
    assert sace1.type == win32security.SYSTEM_AUDIT_ACE_TYPE
    assert not sace1.audit_success
    assert sace1.audit_failure
    assert sace1._trustee.pyobject () == everyone
    assert sace1._access_mask == ntsecuritycon.GENERIC_ALL
    assert sace1.flags == _aces.ACE.FLAGS
    assert sace1.object_type is core.UNSET
    assert sace1.inherited_object_type is core.UNSET

  def test_sace_invalid (self):
    with self.assertRaises (_aces.x_ace):
      _aces.sace (None)

  def test_sace_eq (self):
    assert \
      _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 1))) == \
      _aces.sace ((accounts.principal ("Everyone"), "F", "ALL"))

  def test_sace_ne_trustee (self):
     assert \
      _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 1))) != \
      _aces.sace ((accounts.principal ("Administrators"), "F", "ALL"))

  def test_sace_ne_access (self):
     assert \
      _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 0))) != \
      _aces.sace ((accounts.principal ("Everyone"), "R", (1, 0)))

  def test_sace_ne_type (self):
     assert \
      _aces.sace ((accounts.principal (everyone), ntsecuritycon.GENERIC_ALL, (1, 0))) != \
      _aces.sace ((accounts.principal ("Everyone"), "R", "FAILURE"))

  def test_sace_lt (self):
    assert _aces.sace (("Everyone", "R", (1, 1))) < _aces.sace (("Everyone", "R", (0, 1)))

  def test_sace_as_string (self):
    _aces.sace (("Everyone", "R", "ALL")).as_string ()


  #
  # INHERITED_ACE
  #
  def test_ace_inherited (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags |= win32security.INHERITED_ACE
    assert ace.inherited

  def test_ace_not_inherited (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    assert not ace.inherited

  def test_ace_set_inherited (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    assert not ace.inherited
    ace.inherited = True
    assert ace.flags & win32security.INHERITED_ACE

  def test_ace_reset_inherited (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags |= win32security.INHERITED_ACE
    assert ace.inherited
    ace.inherited = False
    assert not ace.flags & win32security.INHERITED_ACE

  #
  # CONTAINER_INHERIT_ACE
  #
  def test_ace_containers_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags |= win32security.CONTAINER_INHERIT_ACE
    assert ace.containers_inherit

  def test_ace_not_containers_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.CONTAINER_INHERIT_ACE
    assert not ace.containers_inherit

  def test_ace_set_containers_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    ace.flags &= ~win32security.CONTAINER_INHERIT_ACE
    assert not ace.containers_inherit
    ace.containers_inherit = True
    assert ace.flags & win32security.CONTAINER_INHERIT_ACE

  def test_ace_reset_containers_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    ace.flags |= win32security.CONTAINER_INHERIT_ACE
    assert ace.containers_inherit
    ace.containers_inherit = False
    assert not ace.flags & win32security.CONTAINER_INHERIT_ACE

  #
  # OBJECTS_INHERIT_aCE
  #
  def test_ace_objects_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags |= win32security.OBJECT_INHERIT_ACE
    assert ace.objects_inherit

  def test_ace_not_objects_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.OBJECT_INHERIT_ACE
    assert not ace.objects_inherit

  def test_ace_set_objects_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    ace.flags &= ~win32security.OBJECT_INHERIT_ACE
    assert not ace.objects_inherit
    ace.objects_inherit = True
    assert ace.flags & win32security.OBJECT_INHERIT_ACE

  def test_ace_reset_objects_inherit (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    ace.flags &= ~win32security.INHERITED_ACE
    ace.flags |= win32security.OBJECT_INHERIT_ACE
    assert ace.objects_inherit
    ace.objects_inherit = False
    assert not ace.flags & win32security.OBJECT_INHERIT_ACE

  #
  # access
  #
  def test_ace_access_int (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    assert ace._access_mask == ntsecuritycon.GENERIC_ALL
    ace.access = ntsecuritycon.GENERIC_READ
    assert ace._access_mask == ntsecuritycon.GENERIC_READ

  def test_ace_access_string (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    assert ace._access_mask == ntsecuritycon.GENERIC_ALL
    ace.access = "W"
    assert ace._access_mask == ntsecuritycon.GENERIC_WRITE

  #
  # trustee
  #
  def test_ace_trustee_principal (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    assert ace._trustee == everyone
    ace.trustee = me
    assert ace._trustee == me

  def test_ace_trustee_string (self):
    ace = _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE)
    assert ace._trustee == everyone
    ace.trustee = "Administrators"
    assert ace._trustee == administrators

  #
  # ACE constructors
  #
  def test_ace_from_ace_dace (self):
    sd = win32security.GetNamedSecurityInfo (
      self.filename, win32security.SE_FILE_OBJECT,
      win32security.DACL_SECURITY_INFORMATION
    )
    dacl = sd.GetSecurityDescriptorDacl ()
    raw_ace = dacl.GetAce (0)
    ace = _aces.ACE.from_ace (raw_ace)
    assert isinstance (ace, _aces.DACE)
    assert ace.trustee.pyobject () == everyone
    assert ace.access == ntsecuritycon.FILE_READ_DATA
    assert ace.type == win32security.ACCESS_ALLOWED_ACE_TYPE

  def test_ace_from_ace_sace (self):
    sd = win32security.GetNamedSecurityInfo (
      self.filename, win32security.SE_FILE_OBJECT,
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
  def test_ace_set_containers_inherit_inherited (self):
    with self.assertRaises (_aces.exc.x_access_denied):
      _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).containers_inherit = True

  def test_ace_set_objects_inherit_inherited (self):
    with self.assertRaises (_aces.exc.x_access_denied):
      _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).objects_inherit = True

  def test_ace_set_access_inherited (self):
    with self.assertRaises (_aces.exc.x_access_denied):
      _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).access = 0

  def test_ace_set_trustee_inherited (self):
    with self.assertRaises (_aces.exc.x_access_denied):
      _aces.ACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE).trustee = ""

  def test_ace_access_int (self):
    assert _aces.ACE._access (1) == 1

  def test_ace_access_string (self):
    for k, v in _aces.ACE.ACCESS.items ():
      assert _aces.ACE._access (k) == v
    assert _aces.ACE._access ("".join (_aces.ACE.ACCESS.keys ())) == functools.reduce (operator.or_, _aces.ACE.ACCESS.values ())

  def test_ace_access_invalid (self):
    with self.assertRaises (_aces.x_unknown_value):
      assert "*" not in _aces.ACE.ACCESS
      _aces.ACE._access ("*")

  def test_dace_type_int (self):
    assert _aces.DACE._type (1) == 1

  def test_dace_type_string (self):
    for k, v in _aces.DACE.TYPES.items ():
      assert _aces.DACE._type (k) == v

  def test_dace_type_invalid (self):
    with self.assertRaises (_aces.x_unknown_value):
      assert "*" not in _aces.DACE.TYPES
      _aces.DACE._type ("*")

  def test_dace_as_tuple (self):
    dace = _aces.DACE (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)
    assert dace.as_tuple () == (everyone, ntsecuritycon.GENERIC_ALL, win32security.ACCESS_ALLOWED_ACE_TYPE, win32security.INHERITED_ACE)

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
