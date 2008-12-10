import os, sys
import operator

from winsys import _privileges
import win32security

def test_privilege_Privilege ():
  privilege = _privileges.Privilege (win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME))
  assert _privileges.privilege (privilege) is privilege

def test_privilege_int ():
  luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
  assert _privileges.privilege (luid).pyobject () == luid

def test_privilege_string ():
  luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
  assert _privileges.privilege (win32security.SE_BACKUP_NAME).pyobject () == luid

def test_privilege_tuple ():
  luid, attributes = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME), win32security.SE_PRIVILEGE_ENABLED
  privilege = _privileges.privilege ((luid, attributes))
  assert privilege._luid == luid
  assert privilege._attributes == attributes

def test_Privilege_attributes ():
  privilege = _privileges.privilege (win32security.SE_BACKUP_NAME)
  assert privilege.name == win32security.SE_BACKUP_NAME
  assert privilege.description == win32security.LookupPrivilegeDisplayName ("", win32security.SE_BACKUP_NAME)

def test_Privilege_as_string ():
  _privileges.privilege (win32security.SE_BACKUP_NAME).as_string ()

def test_Privilege_eq ():
  assert \
    _privileges.privilege (win32security.SE_BACKUP_NAME) == \
    _privileges.privilege (win32security.SE_BACKUP_NAME)

def test_Privilege_ne ():
  assert \
    _privileges.privilege (win32security.SE_BACKUP_NAME) != \
    _privileges.privilege (win32security.SE_RESTORE_NAME)

def test_Privilege_lt ():
  assert \
    _privileges.privilege (win32security.SE_BACKUP_NAME) < \
    _privileges.privilege (win32security.SE_RESTORE_NAME)

def test_Privilege_pyobject ():
  luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
  assert _privileges.Privilege (luid).pyobject () == luid

def test_Privilege_enabled_unset ():
  luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
  privilege = _privileges.Privilege (luid, 0)
  assert not privilege.enabled and not (privilege._attributes & win32security.SE_PRIVILEGE_ENABLED)

def test_Privilege_enabled_set ():
  luid = win32security.LookupPrivilegeValue ("", win32security.SE_BACKUP_NAME)
  privilege = _privileges.Privilege (luid, win32security.SE_PRIVILEGE_ENABLED)
  assert privilege.enabled and (privilege._attributes & win32security.SE_PRIVILEGE_ENABLED)

if __name__ == '__main__':
  import nose
  nose.runmodule () 
  raw_input ("Press enter...")
