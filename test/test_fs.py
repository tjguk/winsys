from winsys import fs
import win32file
import os
import tempfile


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
  
if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
  