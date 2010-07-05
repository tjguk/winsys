from winsys import fs
import os
import filecmp
import glob
import shutil
import tempfile
import uuid
import win32file
import win32security, ntsecuritycon

TEST_ROOT = os.path.join (tempfile.gettempdir (), uuid.uuid1 ().hex)

#
# Convenience functions
#
def touch (filepath):
  open (os.path.join (TEST_ROOT, filepath), "w").close ()

def mktemp ():
  os.mkdir (TEST_ROOT)

def rmtemp ():
  shutil.rmtree (TEST_ROOT)

def mkdir (filepath):
  os.mkdir (os.path.join (TEST_ROOT, filepath))

def rmdirs (filepath):
  shutil.rmtree (os.path.join (TEST_ROOT, filepath))

def dirs_are_equal (dir1, dir2):
  #
  # Make sure of same directory depth
  #
  if len (list (os.walk (dir1))) != len (list (os.walk (dir2))):
    return False
  #
  # Make sure of directory contents
  #
  for (path1, dirs1, files1), (path2, dirs2, files2) in zip (
    os.walk (dir1), os.walk (dir2)
  ):
    if set (dirs1) != set (dirs2):
      return False
    if set (files1) != set (files2):
      return False
    if any (not files_are_equal (os.path.join (path1, f1), os.path.join (path2, f2)) for f1, f2 in zip (files1, files2)):
      return False
  else:
    return True

def files_are_equal (f1, f2):
  if win32file.GetFileAttributesW (f1) != win32file.GetFileAttributesW (f2):
    return False
  if not filecmp.cmp (f1, f2, False):
    return False
  return True

def deny_access (filepath):
  with fs.entry (filepath).security () as s:
    s.dacl.append (("", "F", "DENY"))

def restore_access (filepath):
  win32security.SetNamedSecurityInfo (
    filepath, win32security.SE_FILE_OBJECT,
    win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION,
    None, None, win32security.ACL (), win32security.ACL ()
  )

def attributes (filepath):
  return win32file.GetFileAttributesW (filepath)

def files_in (filepath):
  return set (f for f in glob.glob (os.path.join (filepath, "*")) if os.path.isfile (f))

def dirs_in (filepath):
  return set (f + "\\" for f in glob.glob (os.path.join (filepath, "*")) if os.path.isdir (f))

def can_encrypt ():
  with tempfile.NamedTemporaryFile (delete=False) as f:
    name = f.name
  try:
    fs.file (name).encrypt ()
  except fs.x_no_certificate:
    return False
  else:
    return True