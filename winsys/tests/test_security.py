from __future__ import with_statement
import os, sys
import contextlib
import tempfile
import unittest
import uuid

import winerror
import win32api
import win32con
import win32event
import win32file
import win32security
import ntsecuritycon
import pywintypes

from winsys.tests import utils
from winsys import security

OPTIONS = \
  security.SECURITY_INFORMATION.OWNER | \
  security.SECURITY_INFORMATION.GROUP | \
  security.SECURITY_INFORMATION.DACL | \
  security.SECURITY_INFORMATION.SACL

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
  return as_string (sd) == str (security)

class TestSecurity (unittest.TestCase):

  #
  # Fixtures
  #
  def setUp (self):
    #
    # If you don't enable SeSecurity, you won't be able to
    # read SACL in this process.
    #
    utils.change_priv (win32security.SE_SECURITY_NAME, True)
    self.GUID = str (uuid.uuid1 ())
    self.TEST_ROOT = tempfile.mkdtemp (prefix="winsys-")
    assert os.path.isdir (self.TEST_ROOT)
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
      self.TEST_ROOT, win32security.SE_FILE_OBJECT,
      win32security.SACL_SECURITY_INFORMATION,
      None, None, None, sacl
    )

  @staticmethod
  def restore_access (filepath):
    win32security.SetNamedSecurityInfo (
      filepath, win32security.SE_FILE_OBJECT,
      win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION |
      win32security.SACL_SECURITY_INFORMATION | win32security.UNPROTECTED_SACL_SECURITY_INFORMATION,
      None, None, win32security.ACL (), win32security.ACL ()
    )

  def tearDown (self):
    for dirpath, dirnames, filenames in os.walk (self.TEST_ROOT, False):
      for filename in filenames:
        filepath = os.path.join (dirpath, filename)
        self.restore_access (filepath)
        os.chmod (filepath, 0o777)
        os.remove (filepath)
      os.rmdir (dirpath)

  @contextlib.contextmanager
  def test_file (self):
    filepath = os.path.join (self.TEST_ROOT, str (uuid.uuid1 ()))
    open (filepath, "w").close ()
    yield filepath
    if os.path.exists (filepath):
      os.remove (filepath)


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
  def test_security_None (self):
    assert security.security (None) is None

  def test_security_default (self):
    assert security.security () == security.Security ()

  def test_security_Security (self):
    s = security.Security ()
    assert security.security (s) is s

  def test_security_HANDLE_file_type (self):
    with self.test_file () as TEST_FILE:
      hFile = handle (TEST_FILE)
      try:
        assert equal (
          win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
          security.security (hFile, security.SE_OBJECT_TYPE.FILE_OBJECT, options=OPTIONS)
        )
      finally:
        hFile.Close ()

  def test_security_HANDLE_no_type (self):
    with self.test_file () as TEST_FILE:
      hFile = handle (TEST_FILE)
      try:
        assert equal (
          win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
          security.security (hFile, options=OPTIONS)
        )
      finally:
        hFile.Close ()

  def test_security_SD (self):
    with self.test_file () as TEST_FILE:
      hFile = handle (TEST_FILE)
      try:
        sa = win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS)
        assert equal (sa, security.security (sa, options=OPTIONS))
      finally:
        hFile.Close ()

  def test_security_string_no_type (self):
    with self.test_file () as TEST_FILE:
      assert equal (
        win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS),
        security.security (TEST_FILE, options=OPTIONS)
      )

  def test_security_string_event (self):
    hEvent = win32event.CreateEvent (None, 0, 0, self.GUID)
    try:
      assert equal (
        win32security.GetNamedSecurityInfo (self.GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
        security.security (self.GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
      )
    finally:
      hEvent.Close ()

  def test_security_nonsense (self):
    with self.assertRaises (security.x_security):
      security.security (object)

  #
  # The Security class has a number of class-level constructors
  # .from_string expects an SDDL string
  # .from_security_descriptor expects a pywin32 security descriptor
  # .from_object expects either an object handle or an object name
  #
  def test_Security_from_string (self):
    with self.test_file () as TEST_FILE:
      sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
      assert equal (sd, security.Security.from_string (as_string (sd), options=OPTIONS))

  def test_Security_from_security_descriptor (self):
    _event = win32event.CreateEvent (None, 0, 0, self.GUID)
    hEvent = win32event.OpenEvent (win32event.EVENT_ALL_ACCESS | win32con.ACCESS_SYSTEM_SECURITY, 0, self.GUID)
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

  def test_Security_from_object_HANDLE (self):
    _event = win32event.CreateEvent (None, 0, 0, self.GUID)
    hEvent = win32event.OpenEvent (win32event.EVENT_ALL_ACCESS | win32con.ACCESS_SYSTEM_SECURITY, 0, self.GUID)
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

  def test_Security_from_object_name (self):
    hEvent = win32event.CreateEvent (None, 0, 0, self.GUID)
    try:
      s = security.Security.from_object (self.GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
      assert equal (
        win32security.GetNamedSecurityInfo (self.GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
        s
      )
      assert s.inherit_handle is True
      assert s._originating_object == self.GUID
      assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
    finally:
      hEvent.Close ()

  def test_Security_no_owner (self):
    with self.assertRaises (security.x_value_not_set):
      security.security ().owner

  def test_Security_no_group (self):
    with self.assertRaises (security.x_value_not_set):
      security.security ().group

  def test_Security_no_dacl (self):
    with self.assertRaises (security.x_value_not_set):
      security.security ().dacl

  def test_Security_no_sacl (self):
    with self.assertRaises (security.x_value_not_set):
      security.security ().sacl

  def test_Security_set_owner_none (self):
    with self.assertRaises (security.x_value_not_set):
      s = security.security ()
      s.owner = None
      s.owner

  def test_Security_set_group_none (self):
    with self.assertRaises (security.x_value_not_set):
      s = security.security ()
      s.group = None
      s.group

  def test_Security_set_dacl_none (self):
    s = security.security ()
    s.dacl = None
    assert s.pyobject ().GetSecurityDescriptorDacl () is None
    sd = win32security.SECURITY_DESCRIPTOR ()
    sd.SetSecurityDescriptorDacl (1, None, 0)
    assert equal (sd, s)

  def test_Security_set_sacl_none (self):
    s = security.security ()
    s.sacl = None
    assert s.pyobject ().GetSecurityDescriptorSacl () is None
    sd = win32security.SECURITY_DESCRIPTOR ()
    sd.SetSecurityDescriptorSacl (1, None, 0)
    assert equal (sd, s)

  def test_Security_set_owner (self):
    administrator = security.principal ("Administrator")
    s = security.security ()
    s.owner = "Administrator"
    assert s.owner == administrator
    sd = win32security.SECURITY_DESCRIPTOR ()
    sd.SetSecurityDescriptorOwner (administrator.pyobject (), 0)
    assert equal (sd, s)

  def test_Security_set_group (self):
    everyone = security.principal ("Everyone")
    s = security.security ()
    s.group = "Everyone"
    assert s.group == everyone
    sd = win32security.SECURITY_DESCRIPTOR ()
    sd.SetSecurityDescriptorGroup (everyone.pyobject (), 0)
    assert equal (sd, s)

  def test_Security_set_dacl_empty (self):
    s = security.security ()
    s.dacl = []
    assert len (s.dacl) == 0
    assert s.pyobject ().GetSecurityDescriptorDacl ().GetAceCount () == 0
    sd = win32security.SECURITY_DESCRIPTOR ()
    acl = win32security.ACL ()
    sd.SetSecurityDescriptorDacl (1, acl, 0)
    assert equal (sd, s)

  def test_Security_set_sacl_empty (self):
    s = security.security ()
    s.sacl = []
    assert len (s.sacl) == 0
    assert s.pyobject ().GetSecurityDescriptorSacl ().GetAceCount () == 0
    sd = win32security.SECURITY_DESCRIPTOR ()
    acl = win32security.ACL ()
    sd.SetSecurityDescriptorSacl (1, acl, 0)
    assert equal (sd, s)

  def test_Security_add_to_dacl_simple (self):
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

  def test_Security_add_to_sacl_simple (self):
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

  def test_Security_break_dacl_inheritance_no_copy (self):
    with self.test_file () as filepath:
      s = security.security (filepath, options=OPTIONS)
      assert s.dacl.inherited
      s.break_inheritance (copy_first=False, break_dacl=True, break_sacl=False)
      s.to_object ()
      sd = win32security.GetNamedSecurityInfo (filepath, win32security.SE_FILE_OBJECT, OPTIONS)
      assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
      assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
      assert sd.GetSecurityDescriptorDacl ().GetAceCount () == 0

  def test_Security_break_dacl_inheritance_copy (self):
    with self.test_file () as TEST_FILE:
      s = security.security (TEST_FILE, options=OPTIONS)
      n_aces = len (s.dacl)
      assert s.dacl.inherited
      s.break_inheritance (copy_first=True, break_dacl=True, break_sacl=False)
      s.to_object ()
      sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
      assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
      assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
      assert sd.GetSecurityDescriptorDacl ().GetAceCount () == n_aces

  def test_Security_break_sacl_inheritance_no_copy (self):
    with self.test_file () as TEST_FILE:
      s = security.security (TEST_FILE, options=OPTIONS)
      assert s.sacl.inherited
      s.break_inheritance (copy_first=False, break_dacl=False, break_sacl=True)
      s.to_object ()
      sd = win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS)
      assert (sd.GetSecurityDescriptorControl ()[0] & win32security.SE_SACL_PROTECTED)
      assert (not sd.GetSecurityDescriptorControl ()[0] & win32security.SE_DACL_PROTECTED)
      assert sd.GetSecurityDescriptorSacl ().GetAceCount () == 0

  def test_Security_break_sacl_inheritance_copy (self):
    with self.test_file () as TEST_FILE:
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
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
