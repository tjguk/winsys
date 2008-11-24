import os, sys
from nose.tools import *
import winerror
import win32api
import win32con
import win32security
import ntsecuritycon
import pywintypes

import tempfile
import uuid

from winsys import registry, utils

GUID = str (uuid.uuid1 ())
TEST_ROOT = tempfile.mkdtemp (prefix="winsys-")
print TEST_ROOT
TEST_FILE = os.path.join (TEST_ROOT, "file.txt")
TEST1_DIR = os.path.join (TEST_ROOT, "dir1")
TEST1_FILE = os.path.join (TEST1_DIR, "file1.txt")
TEST2_DIR = os.path.join (TEST1_DIR, "dir2")
TEST2_FILE = os.path.join (TEST2_DIR, "file2.txt")

#
# Fixtures
#
def setup ():
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

def test_nothing ():
  pass
