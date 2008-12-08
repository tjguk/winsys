import os, sys
from nose.tools import *
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

from winsys import security

GUID = str (uuid.uuid1 ())
TEST_ROOT = tempfile.mkdtemp (prefix="winsys-")
TEST_FILE = os.path.join (TEST_ROOT, "file.txt")
TEST1_DIR = os.path.join (TEST_ROOT, "dir1")
TEST1_FILE = os.path.join (TEST1_DIR, "file1.txt")
TEST2_DIR = os.path.join (TEST1_DIR, "dir2")
TEST2_FILE = os.path.join (TEST2_DIR, "file2.txt")

OPTIONS = \
  security.SECURITY_INFORMATION.OWNER | \
  security.SECURITY_INFORMATION.GROUP | \
  security.SECURITY_INFORMATION.DACL | \
  security.SECURITY_INFORMATION.SACL 

def handle (filepath):
  return win32file.CreateFile (
    filepath,
    ntsecuritycon.GENERIC_READ | win32con.ACCESS_SYSTEM_SECURITY,
    win32file.FILE_SHARE_READ,
    None,
    win32con.OPEN_EXISTING,
    win32file.FILE_ATTRIBUTE_NORMAL,
    None
  )

#
# Fixtures
#
SECURITY_PRIV = win32security.LookupPrivilegeValue (None, win32security.SE_SECURITY_NAME)
def setup ():
  hToken = win32security.OpenProcessToken (
    win32api.GetCurrentProcess (), 
    ntsecuritycon.MAXIMUM_ALLOWED
  )
  win32security.AdjustTokenPrivileges ( 
    hToken,
    False, 
    [(SECURITY_PRIV, win32security.SE_PRIVILEGE_ENABLED)]
  )
  assert os.path.isdir (TEST_ROOT)
  open (TEST_FILE, "w").close ()
  os.mkdir (TEST1_DIR)
  open (TEST1_FILE, "w").close ()
  os.mkdir (TEST2_DIR)
  open (TEST2_FILE, "w").close ()
  
def teardown ():
  dacl = win32security.ACL ()
  sid, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())
  dacl.AddAccessAllowedAce (win32security.ACL_REVISION_DS, ntsecuritycon.FILE_ALL_ACCESS, sid)
  def remove (path):
    win32security.SetNamedSecurityInfo (
      path, win32security.SE_FILE_OBJECT, 
      win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION, 
      None, None, dacl, None
    )
    if os.path.isdir (path):
      os.rmdir (path)
    else:
      os.unlink (path)

  remove (TEST2_FILE)
  remove (TEST2_DIR)
  remove (TEST1_FILE)
  remove (TEST1_DIR)
  remove (TEST_FILE)
  remove (TEST_ROOT)

  win32security.AdjustTokenPrivileges ( 
    win32security.OpenProcessToken (win32api.GetCurrentProcess (), ntsecuritycon.MAXIMUM_ALLOWED),
    False, 
    [(SECURITY_PRIV, 0)]
  )

def test_security_None ():
  assert security.security (None) is None

def test_security_object ():
  assert security.security () == security.Security ()

def test_security_Security ():
  s = security.Security ()
  assert security.security (s) is s

def test_security_HANDLE_file_type ():
  hFile = handle (TEST_FILE)
  try:
    s0 = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
      win32security.SDDL_REVISION_1,
      OPTIONS
    )
    s1 = str (security.security (hFile, security.SE_OBJECT_TYPE.FILE_OBJECT, options=OPTIONS))
    print s0
    print s1
    assert s0 == s1
    #~ assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      #~ win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
      #~ win32security.SDDL_REVISION_1,
      #~ OPTIONS
    #~ ) == str (security.security (hFile, security.SE_OBJECT_TYPE.FILE_OBJECT, options=OPTIONS))
  finally:
    hFile.Close ()

def test_security_HANDLE_no_type ():
  hFile = handle (TEST_FILE)
  try:
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (security.security (hFile, options=OPTIONS))
  finally:
    hFile.Close ()

def test_security_SD ():
  hFile = handle (TEST_FILE)
  try:
    sa = win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS)
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      sa,
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (security.security (sa, options=OPTIONS))
  finally:
    hFile.Close ()

def test_security_string_no_type ():
  assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
    win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS),
    win32security.SDDL_REVISION_1,
    OPTIONS
  ) == str (security.security (TEST_FILE, options=OPTIONS))

def test_security_string_event ():
  hEvent = win32event.CreateEvent (None, 0, 0, GUID)
  try:
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      win32security.GetNamedSecurityInfo (GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (security.security (GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS))
  finally:
    hEvent.Close ()
    
@raises (security.x_security)
def test_security_nonsense ():
  security.security (object)

def test_Security_from_string ():
  string = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
    win32security.GetNamedSecurityInfo (TEST_FILE, win32security.SE_FILE_OBJECT, OPTIONS),
    win32security.SDDL_REVISION_1,
    OPTIONS
  )
  assert string == str (security.Security.from_string (string, options=OPTIONS))

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
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      sd, 
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (s)
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
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      win32security.GetSecurityInfo (hEvent, win32security.SE_KERNEL_OBJECT, OPTIONS),
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (s)
    assert s.inherit_handle is True
    assert s._originating_object == hEvent
    assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
  finally:
    hEvent.Close ()

def test_Security_from_object_name ():
  hEvent = win32event.CreateEvent (None, 0, 0, GUID)
  try:
    s = security.Security.from_object (GUID, security.SE_OBJECT_TYPE.KERNEL_OBJECT, options=OPTIONS)
    assert win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
      win32security.GetNamedSecurityInfo (GUID, win32security.SE_KERNEL_OBJECT, OPTIONS),
      win32security.SDDL_REVISION_1,
      OPTIONS
    ) == str (s)
    assert s.inherit_handle is True
    assert s._originating_object == GUID
    assert s._originating_object_type == win32security.SE_KERNEL_OBJECT
  finally:
    hEvent.Close ()