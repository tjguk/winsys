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

import utils
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

  utils.change_priv (win32security.SE_SECURITY_NAME, False)

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
  hFile = handle (TEST_FILE)
  try:
    assert equal (
      win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
      security.security (hFile, security.SE_OBJECT_TYPE.FILE_OBJECT, options=OPTIONS)
    )
  finally:
    hFile.Close ()

def test_security_HANDLE_no_type ():
  hFile = handle (TEST_FILE)
  try:
    assert equal (
      win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS),
      security.security (hFile, options=OPTIONS)
    )
  finally:
    hFile.Close ()

def test_security_SD ():
  hFile = handle (TEST_FILE)
  try:
    sa = win32security.GetSecurityInfo (hFile, win32security.SE_FILE_OBJECT, OPTIONS)
    assert equal (sa, security.security (sa, options=OPTIONS))
  finally:
    hFile.Close ()

def test_security_string_no_type ():
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
  
if __name__ == '__main__':
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
