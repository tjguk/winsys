import os, sys
import operator

import win32api
import win32con
import win32security
import ntsecuritycon
import tempfile
import unittest

from winsys import accounts
from winsys._security import _aces, _acls

everyone, _, _ = win32security.LookupAccountName (None, "Everyone")
me, _, _ = win32security.LookupAccountName (None, win32api.GetUserNameEx (win32con.NameSamCompatible))

class TestACLs (unittest.TestCase):

  def test_acl_None (self):
    acl = _acls.acl (None)
    assert isinstance (acl, _acls.ACL) and acl.pyobject () is None

  def test_acl_PyACL (self):
    dacl = win32security.ACL ()
    dacl.AddAccessAllowedAceEx (win32security.ACL_REVISION_DS, 0, ntsecuritycon.FILE_READ_DATA, everyone)
    acl = _acls.acl (dacl).pyobject ()
    assert dacl.GetAceCount () == 1
    assert dacl.GetAce (0) == ((win32security.ACCESS_ALLOWED_ACE_TYPE, 0), ntsecuritycon.FILE_READ_DATA, everyone)

  def test_acl_ACL (self):
    acl0 = _acls.ACL ()
    acl = _acls.acl (acl0)
    assert acl is acl0

  def test_acl_iterable (self):
    daces0 = [("Everyone", "R", "Allow"), ("Administrators", "F", "Allow")]
    def iteraces ():
      for dace in daces0:
        yield dace
    assert list (_acls.dacl (iteraces ())) == list (_aces.dace (dace) for dace in daces0)

  def test_ACL_iterated (self):
    #
    # This includes a test for sorting, putting deny records first
    #
    acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
    assert list (acl) == [
      _aces.dace (("Administrators", "F", "Deny")),
      _aces.dace (("Everyone", "R", "Allow"))
    ]

  def test_ACL_append (self):
    acl = _acls.acl ([("Everyone", "R", "Allow")])
    acl.append (("Administrators", "F", "Deny"))
    assert list (acl) == [
      _aces.dace (("Administrators", "F", "Deny")),
      _aces.dace (("Everyone", "R", "Allow"))
    ]

  def test_ACL_getitem (self):
    acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
    #
    # Note that the list is *stored* in the order entered; it
    # is only returned (via pyobject) in sorted order.
    #
    assert acl[0] == ("Everyone", "R", "Allow")

  def test_ACL_setitem (self):
    acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
    acl[0] = ((me, "R", "Allow"))
    assert acl[0] == (me, "R", "Allow")

  def test_ACL_delitem (self):
    acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
    del acl[0]
    assert list (acl) == [
      _aces.dace (("Administrators", "F", "Deny")),
    ]

  def test_ACL_len (self):
    aces = [("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")]
    acl = _acls.acl (aces)
    assert len (acl) == len (aces)

  def test_ACL_nonzero (self):
    assert not _acls.acl (None)
    assert not _acls.acl ([])
    assert _acls.acl ([("Everyone", "R", "Allow")])

  def test_ACL_contains (self):
    aces = [("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")]
    acl = _acls.acl (aces)
    for ace in aces:
      assert ace in acl
    assert ("Everyone", "F", "Deny") not in acl

  def test_DACL_public (self):
    acl = _acls.DACL.public ()
    assert list (acl) == [("Everyone", "F", "ALLOW")]

  def test_DACL_private (self):
    acl = _acls.DACL.private ()
    assert list (acl) == [(me, "F", "ALLOW")]

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty ():
    raw_input ("Press enter...")
