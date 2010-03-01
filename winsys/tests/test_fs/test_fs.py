from winsys import fs
import os
import filecmp
import shutil
import tempfile
import uuid
import win32file

#
# Convenience functions
#
def touch (filepath):
  open (os.path.join (TEST_ROOT, filepath), "w").close ()

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

def setup ():
  global TEST_ROOT
  TEST_ROOT = tempfile.mkdtemp ()
  print TEST_ROOT

def teardown ():
  rmdirs (TEST_ROOT)

def test_FileAttributes():
  TempFile=os.path.expandvars("%temp%\\FileAtr.txt")
  try:
    open(TempFile,"w").close()
    assert win32file.GetFileAttributesW(TempFile)==fs.entry(TempFile).attributes.flags
  finally:
    os.unlink(TempFile)

def test_FileTempAttributes():
  TempFile=tempfile.NamedTemporaryFile()
  assert win32file.GetFileAttributesW(TempFile.name)==fs.entry(TempFile.name).attributes.flags

def test_dir_copy_to_new_dir ():
  source_name = uuid.uuid1 ().hex
  target_name = uuid.uuid1 ().hex
  source = os.path.join (TEST_ROOT, source_name)
  target = os.path.join (TEST_ROOT, target_name)
  os.mkdir (source)
  assert os.path.isdir (source)
  assert not os.path.isdir (target)
  fs.copy (source, target)
  assert dirs_are_equal (source, target)

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
