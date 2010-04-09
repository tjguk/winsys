from __future__ import with_statement
import os, sys
from nose.tools import *
import contextlib
import winerror
import win32api
import win32con
import win32event
import win32file
import win32security
import ntsecuritycon
import pywintypes

import tempfile
import uuid

import utils
from winsys import security

GUID = str (uuid.uuid1 ())
TEST_ROOT = tempfile.mkdtemp (prefix="winsys-")

OPTIONS = \
  security.SECURITY_INFORMATION.OWNER | \
  security.SECURITY_INFORMATION.GROUP | \
  security.SECURITY_INFORMATION.DACL | \
  security.SECURITY_INFORMATION.SACL

@contextlib.contextmanager
def test_file ():
  filepath = os.path.join (TEST_ROOT, str (uuid.uuid1 ()))
  open (filepath, "w").close ()
  yield filepath
  if os.path.exists (filepath):
    os.remove (filepath)

#
# convenience functions
#
def handle (filepath):
  return win32file.CreateFile (
    filepath,
    #
    # If you don't specify ACCESS_SYSTEM_SECURITY, you won't be able
    # to read the SACL via this handle.
    #
    ntsecuritycon.GENERIC_READ | win32con.ACCESS_SYSTEM_SECURITY,
    win32file.FILE_SHARE_READ,
    None,
    win32con.OPEN_EXISTING,
    win32file.FILE_ATTRIBUTE_NORMAL,
    None
  )

def as_string (sd):
  return win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
    sd, win32security.SDDL_REVISION_1, OPTIONS
  )

def equal (sd, security):
  print as_string (sd)
  print str (security)
  return as_string (sd) == str (security)

#
# Fixtures
#
def setup ():
  #
  # If you don't enable SeSecurity, you won't be able to
  # read SACL in this process.
  #
  utils.change_priv (win32security.SE_SECURITY_NAME, True)
  assert os.path.isdir (TEST_ROOT)
  sacl = win32security.ACL ()
  sid, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())
  sacl.AddAuditAccessAceEx (
    win32security.ACL_REVISION_DS,
    win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE,
    ntsecuritycon.FILE_ALL_ACCESS,
    sid,
    1, 1
  )
  win32security.SetNamedSecurityInfo (
    TEST_ROOT, win32security.SE_FILE_OBJECT,
    win32security.SACL_SECURITY_INFORMATION,
    None, None, None, sacl
  )

def restore_access (filepath):
  win32security.SetNamedSecurityInfo (
    filepath, win32security.SE_FILE_OBJECT,
    win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION |
    win32security.SACL_SECURITY_INFORMATION | win32security.UNPROTECTED_SACL_SECURITY_INFORMATION,
    None, None, win32security.ACL (), win32security.ACL ()
  )

def teardown ():
  for dirpath, dirnames, filenames in os.walk (TEST_ROOT, False):
    for filename in filenames:
      filepath = os.path.join (dirpath, filename)
      restore_access (filepath)
      os.chmod (filepath, 0777)
      os.remove (filepath)
    os.rmdir (dirpath)


#
# The security function should convert its argument to something
# useful:
#
# None is return unchanged
# (default) returns an empty Security instance
# a Security instance is returned unchanged
# a handle specified as a file returns a corresponding Security instance
# an unspecified handle is assumed to be a file and the corresponding Security instance returned
# a pywin32 security descriptor returns the corresponding Security object
# a filename operates like an unspecified handle
# a name specified as something other than a file returns the corresponding Security object
# anything else should raise an x_security exception
#
def test_security_None ():
  assert security.security (None) is None

def test_security_default ():
  assert security.security () == security.Security ()

def test_security_Security ():
  s = security.Security ()
  assert security.security (s) is s

def test_security_HANDLE_file_type ():
  with test_file () as TEST_FILE:
    hFile = handle (TEST_FILE)
    try:
      assert equal (
        win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
        security.security (hFile, security.SE_OBJECT_TYPE.FILE_OBJECT, options=OPTIONS)
      )
    finally:
      hFile.Close ()

def test_security_HANDLE_no_type ():
  with test_file () as TEST_FILE:
    hFile = handle (TEST_FILE)
    try:
      assert equal (
        win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
        security.security (hFile, options=OPTIONS)
      )
    finally:
      hFile.Close ()

def test_security_SD ():
  with test_file () as TEST_FILE:
    hFile = handle (TEST_FILE)
    try:
      sa = win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS)
      assert equal (sa, security.security (sa, options=OPTIONS))
    finally:
      hFile.Close ()

def test_security_string_no_type ():
  with test_file () as TEST_FILE:
    assert equal (
      win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS),
      security.security (TEST_FILE, options=OPTIONS)
    )

def test_security_string_event ():
  hEvent = win32event.CreateEvent (None, 0, 0, GUID)
  try:
    assert equal (
      win32security.GetNamedSecurityInfo (GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
      security.security (GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
    )
  finally:
    hEvent.Close ()

@raises (security.x_security)
def test_security_nonsense ():
  security.security (object)

#
# The Security class has a number of class-level constructors
# .from_string expects an SDDL string
# .from_security_descriptor expects a pywin32 security descriptor
# .from_object expects either an object handle or an object name
#
def test_Security_from_string ():
  with test_file () as TEST_FILE:
    sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
    assert equal (sd, security.Security.from_string (as_string (sd), options=OPTIONS))

def test_Security_from_security_descriptor ():
  _event = win32event.CreateEvent (None, 0, 0, GUID)
  hEvent = win32event.OpenEvent (win32event.EVENT_ALL_ACCESS | win32con.ACCESS_SYSTEM_SECURITY, 0, GUID)
  try:
    sd = win32security.GetSecurityInfo (
      hEvent,
      win32security.SE_KERNEL_OBJECT, OPTIONS
    )
    s = security.Security.from_security_descriptor (
      sd,
      originating_object=hEvent,
      originating_object_type=security.SE_OBJECT_TYPE.KERNEL_OBJECT,
      options=OPTIONS
    )
    assert equal (sd, s)
    assert s.inherit_handle is True
    assert s._originating_object is hEvent
    assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
  finally:
    hEvent.Close ()

def test_Security_from_object_HANDLE ():
  _event = win32event.CreateEvent (None, 0, 0, GUID)
  hEvent = win32event.OpenEvent (win32event.EVENT_ALL_ACCESS | win32con.ACCESS_SYSTEM_SECURITY, 0, GUID)
  try:
    s = security.Security.from_object (hEvent, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
    assert equal (
      win32security.GetSecurityInfo (hEvent, win32security.SE_KERNEL_OBJECT, OPTIONS),
      s
    )
    assert s.inherit_handle is True
    assert s._originating_object == hEvent
    assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
  finally:
    hEvent.Close ()

def test_Security_from_object_name ():
  hEvent = win32event.CreateEvent (None, 0, 0, GUID)
  try:
    s = security.Security.from_object (GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
    assert equal (
      win32security.GetNamedSecurityInfo (GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
      s
    )
    assert s.inherit_handle is True
    assert s._originating_object == GUID
    assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
  finally:
    hEvent.Close ()

@raises (security.x_value_not_set)
def test_Security_no_owner ():
  security.security ().owner

@raises (security.x_value_not_set)
def test_Security_no_group ():
  security.security ().group

@raises (security.x_value_not_set)
def test_Security_no_dacl ():
  security.security ().dacl

@raises (security.x_value_not_set)
def test_Security_no_sacl ():
  security.security ().sacl

@raises (security.x_value_not_set)
def test_Security_set_owner_none ():
  s = security.security ()
  s.owner = None
  s.owner

@raises (security.x_value_not_set)
def test_Security_set_group_none ():
  s = security.security ()
  s.group = None
  s.group

def test_Security_set_dacl_none ():
  s = security.security ()
  s.dacl = None
  assert s.pyobject ().GetSecurityDescriptorDacl () is None
  sd = win32security.SECURITY_DESCRIPTOR ()
  sd.SetSecurityDescriptorDacl (1, None, 0)
  assert equal (sd, s)

def test_Security_set_sacl_none ():
  s = security.security ()
  s.sacl = None
  assert s.pyobject ().GetSecurityDescriptorSacl () is None
  sd = win32security.SECURITY_DESCRIPTOR ()
  sd.SetSecurityDescriptorSacl (1, None, 0)
  assert equal (sd, s)

def test_Security_set_owner ():
  administrator = security.principal ("Administrator")
  s = security.security ()
  s.owner = "Administrator"
  assert s.owner == administrator
  sd = win32security.SECURITY_DESCRIPTOR ()
  sd.SetSecurityDescriptorOwner (administrator.pyobject (), 0)
  assert equal (sd, s)

def test_Security_set_group ():
  everyone = security.principal ("Everyone")
  s = security.security ()
  s.group = "Everyone"
  assert s.group == everyone
  sd = win32security.SECURITY_DESCRIPTOR ()
  sd.SetSecurityDescriptorGroup (everyone.pyobject (), 0)
  assert equal (sd, s)

def test_Security_set_dacl_empty ():
  s = security.security ()
  s.dacl = []
  assert len (s.dacl) == 0
  assert s.pyobject ().GetSecurityDescriptorDacl ().GetAceCount () == 0
  sd = win32security.SECURITY_DESCRIPTOR ()
  acl = win32security.ACL ()
  sd.SetSecurityDescriptorDacl (1, acl, 0)
  assert equal (sd, s)

def test_Security_set_sacl_empty ():
  s = security.security ()
  s.sacl = []
  assert len (s.sacl) == 0
  assert s.pyobject ().GetSecurityDescriptorSacl ().GetAceCount () == 0
  sd = win32security.SECURITY_DESCRIPTOR ()
  acl = win32security.ACL ()
  sd.SetSecurityDescriptorSacl (1, acl, 0)
  assert equal (sd, s)

def test_Security_add_to_dacl_simple ():
  administrator = security.principal ("Administrator")
  s = security.security ()
  s.dacl = []
  s.dacl.append (("Administrator", "F", "ALLOW"))
  sd = win32security.SECURITY_DESCRIPTOR ()
  dacl = win32security.ACL ()
  dacl.AddAccessAllowedAceEx (
    win32security.ACL_REVISION_DS,
    security.DACE.FLAGS,
    ntsecuritycon.GENERIC_ALL,
    administrator.pyobject ()
  )
  sd.SetSecurityDescriptorDacl (1, dacl, 0)
  assert equal (sd, s)

def test_Security_add_to_sacl_simple ():
  administrator = security.principal ("Administrator")
  s = security.security ()
  s.sacl = []
  s.sacl.append (("Administrator", "F", "SUCCESS"))
  sd = win32security.SECURITY_DESCRIPTOR ()
  sacl = win32security.ACL ()
  sacl.AddAuditAccessAceEx (
    win32security.ACL_REVISION_DS,
    security.SACE.FLAGS,
    ntsecuritycon.GENERIC_ALL,
    administrator.pyobject (),
    1, 0
  )
  sd.SetSecurityDescriptorSacl (1, sacl, 0)
  assert equal (sd, s)

def test_Security_break_dacl_inheritance_no_copy ():
  with test_file () as filepath:
    s = security.security (filepath, options=OPTIONS)
    assert s.dacl.inherited
    s.break_inheritance (copy_first=False, break_dacl=True, break_sacl=False)
    s.to_object ()
    sd = win32security.GetNamedSecurityInfo (filepath, win32security.SE_FILE_OBJECT, OPTIONS)
    assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
    assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
    assert sd.GetSecurityDescriptorDacl ().GetAceCount () == 0

def test_Security_break_dacl_inheritance_copy ():
  with test_file () as TEST_FILE:
    s = security.security (TEST_FILE, options=OPTIONS)
    n_aces = len (s.dacl)
    assert s.dacl.inherited
    s.break_inheritance (copy_first=True, break_dacl=True, break_sacl=False)
    s.to_object ()
    sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
    assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
    assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
    assert sd.GetSecurityDescriptorDacl ().GetAceCount () == n_aces

def test_Security_break_sacl_inheritance_no_copy ():
  with test_file () as TEST_FILE:
    s = security.security (TEST_FILE, options=OPTIONS)
    assert s.sacl.inherited
    s.break_inheritance (copy_first=False, break_dacl=False, break_sacl=True)
    s.to_object ()
    sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
    assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
    assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
    assert sd.GetSecurityDescriptorSacl ().GetAceCount () == 0

def test_Security_break_sacl_inheritance_copy ():
  with test_file () as TEST_FILE:
    s = security.security (TEST_FILE, options=OPTIONS)
    n_aces = len (s.sacl)
    assert s.sacl.inherited
    s.break_inheritance (copy_first=True, break_dacl=False, break_sacl=True)
    s.to_object ()
    sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
    assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
    assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
    assert sd.GetSecurityDescriptorSacl ().GetAceCount () == n_aces

if __name__ == "__main__":
  import nose, sys
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
