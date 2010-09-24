import os, sys
import operator
import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0

from winsys._security import _privileges
import win32security

class TestPrivileges (unittest.TestCase):

  @staticmethod
  def _token_privs ():
    token = _privileges._get_token ()
    return dict (win32security.GetTokenInformation (token, win32security.TokenPrivileges))

  def test_privilege_Privilege (self):
    privilege = _privileges.Privilege (win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME))
    assert _privileges.privilege (privilege) is privilege

  def test_privilege_int (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    assert _privileges.privilege (luid).pyobject () == luid

  def test_privilege_string (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    assert _privileges.privilege (win32security.SE_BACKUP_NAME).pyobject () == luid

  def test_privilege_constant (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    assert _privileges.privilege ("backup").pyobject () == luid

  def test_privilege_tuple (self):
    luid, attributes = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME), win32security.SE_PRIVILEGE_ENABLED
    privilege = _privileges.privilege ((luid, attributes))
    assert privilege._luid == luid
    assert privilege._attributes == attributes

  def test_Privilege_attributes (self):
    privilege = _privileges.privilege (win32security.SE_BACKUP_NAME)
    assert privilege.name == win32security.SE_BACKUP_NAME
    assert privilege.description == win32security.LookupPrivilegeDisplayName ("", win32security.SE_BACKUP_NAME)

  def test_Privilege_as_string (self):
    _privileges.privilege (win32security.SE_BACKUP_NAME).as_string ()

  def test_Privilege_eq (self):
    assert \
      _privileges.privilege (win32security.SE_BACKUP_NAME) == \
      _privileges.privilege (win32security.SE_BACKUP_NAME)
    assert not \
      _privileges.privilege (win32security.SE_BACKUP_NAME) == \
      _privileges.privilege (win32security.SE_RESTORE_NAME)

  def test_Privilege_ne (self):
    assert \
      _privileges.privilege (win32security.SE_BACKUP_NAME) != \
      _privileges.privilege (win32security.SE_RESTORE_NAME)
    assert not \
      _privileges.privilege (win32security.SE_BACKUP_NAME) != \
      _privileges.privilege (win32security.SE_BACKUP_NAME)

  def test_Privilege_lt (self):
    assert \
      _privileges.privilege (win32security.SE_BACKUP_NAME) < \
      _privileges.privilege (win32security.SE_RESTORE_NAME)

  def test_Privilege_pyobject (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    assert _privileges.Privilege (luid).pyobject () == luid

  def test_Privilege_enabled_unset (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    privilege = _privileges.Privilege (luid, 0)
    assert not privilege.enabled and not (privilege._attributes & win32security.SE_PRIVILEGE_ENABLED)

  def test_Privilege_enabled_set (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    privilege = _privileges.Privilege (luid, win32security.SE_PRIVILEGE_ENABLED)
    assert privilege.enabled and (privilege._attributes & win32security.SE_PRIVILEGE_ENABLED)

  def test_Privilege_context (self):
    luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
    assert not bool (self._token_privs ()[luid])
    with _privileges.privilege (luid) as p:
      assert bool (self._token_privs ()[luid])
    assert not bool (self._token_privs ()[luid])

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
