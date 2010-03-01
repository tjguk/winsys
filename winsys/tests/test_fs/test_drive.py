import os, sys
import tempfile
import win32file

from winsys import fs

from nose.tools import *
from nose.plugins import skip

#
# The name of the drive should be normalised:
# lowercase-letter;colon;backslash
#
def test_name ():
  names = ["C", "C:", "C:/", "C:\\"]
  for name in names:
    assert_equals (fs.drive (name).name, "c:\\")
    assert_equals (fs.drive (name.lower ()).name, "c:\\")

def test_DriveType ():
  assert_equals (fs.drive ("C:").type, win32file.GetDriveTypeW ("C:"))

def test_DriveRoot ():
  assert_equals (fs.drive ("C:").root, fs.dir (u"C:\\"))

def test_volume ():
  assert_equals (fs.drive ("C:").volume.name, win32file.GetVolumeNameForVolumeMountPoint ("C:\\"))

def test_mount ():
  #
  # Difficult to test because it's not possible
  # to mount a volume on two drive letters simultaneously.
  # Try to find something unimportant, like a CDROM, and
  # dismount it before remounting it.
  #
  raise skip.SkipTest

def test_dismount ():
  #
  # Likewise difficult to test because destructive
  #
  raise skip.SkipTest

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
