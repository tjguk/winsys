import os, sys
import tempfile
import win32file

from winsys import fs

from nose.tools import *

def test_DriveType ():
  assert_equals (fs.drive ("C:").type, win32file.GetDriveTypeW ("C:"))

def test_DriveRoot ():
  assert_equals (fs.drive ("C:").root(), fs.dir (u"C:\\"))

def test_volume ():
  assert_equals (fs.drive ("C:").volume.name, win32file.GetVolumeNameForVolumeMountPoint ("C:\\"))

def test_mount ():
  #
  # Difficult to test because it's not possible
  # to mount a volume on two drive letters simultaneously.
  # Try to find something unimportant, like a CDROM, and
  # dismount it before remounting it.
  #

def test_mount_to_empty_folder ():
  test = tempfile.mkdtemp ()
  fs.drive ("c").
  
  
  mounts = dict (fs.mounts ())
  for letter in "bcdefghijklmnopqrstuvwxwxyz":
    if letter not in mounts:
      drive = fs.drive (letter)
      break
  else:
    raise RuntimeError ("Unable to find a spare drive letter")
  drive.mount (fs.drive (fs.filepath (sys.executable).root).volume)
  
if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
