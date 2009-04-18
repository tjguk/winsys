from winsys import fs
import win32file
import os
import shutil
import tempfile
import uuid

#
# Convenience functions
#
def touch (filepath):
  open (os.path.join (TEST_ROOT, filepath), "w").close ()
  
def mkdir (filepath):
  os.mkdir (os.path.join (TEST_ROOT, filepath))
  
def rmdirs (filepath):
  shutil.rmtree (os.path.join (TEST_ROOT, filepath))
  
def setup ():
  global TEST_ROOT
  TEST_ROOT = tempfile.mkdtemp ()
  print TEST_ROOT
  mkdir ("a")
  touch ("a/a.txt")
  mkdir ("a/b")
  touch ("a/b/b.txt")
  mkdir ("a/b/c")
  touch ("a/b/c/c.txt")
  
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

def test_DriveName():
  assert fs.Drive("C:").name == u"C:\\"

def test_DriveNameBack():
  assert fs.Drive("C:\\").name ==u"C:\\"

def test_DriveNameForward():
  assert fs.Drive("C:/").name==u"C:\\"

def test_DriveNameLower():
  assert fs.Drive("c:\\").name == "C:\\"

def test_DriveType():
  assert fs.Drive("C:").type==win32file.GetDriveTypeW("C:")

def test_Drive_as_String():
 assert fs.Drive("C:")==u'Drive C:\\'
 
def test_DriveRoot():
  assert fs.Drive("C:").root()=="Dir: C:\\"
  
def test_dir_copy ():
  target_name = uuid.uuid1 ().hex
  source = os.path.join (TEST_ROOT, "a")
  target = os.path.join (TEST_ROOT, target_name)
  assert not os.path.isdir (target)
  fs.copy (source, target)
  #
  # Make sure of same directory depth
  #
  assert len (list (os.walk (source))) == len (list (os.walk (target)))
  #
  # Make sure of directory contents
  #
  for (source_path, source_dirs, source_files), (target_path, target_dirs, target_files) in zip (
    os.walk (source), os.walk (target)
  ):
    assert set (source_dirs) == set (target_dirs)
    assert set (source_files) == set (target_files)
  
if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
  