import os, sys
import tempfile
import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0

import win32file

from winsys import fs

class TestDrive (unittest.TestCase):

  #
  # The name of the drive should be normalised:
  # lowercase-letter;colon;backslash
  #
  def test_name (self):
    names = ["C", "C:", "C:/", "C:\\"]
    for name in names:
      self.assertEquals (fs.drive (name).name, "c:\\")
      self.assertEquals (fs.drive (name.lower ()).name, "c:\\")

  def test_DriveType (self):
    self.assertEquals (fs.drive ("C:").type, win32file.GetDriveTypeW ("C:"))

  def test_DriveRoot (self):
    self.assertEquals (fs.drive ("C:").root, fs.dir ("C:\\"))

  def test_volume (self):
    self.assertEquals (fs.drive ("C:").volume.name, win32file.GetVolumeNameForVolumeMountPoint ("C:\\"))

  @unittest.skip ("Skip destructive test")
  def test_mount (self):
    #
    # Difficult to test because it's not possible
    # to mount a volume on two drive letters simultaneously.
    # Try to find something unimportant, like a CDROM, and
    # dismount it before remounting it.
    #
    pass

  @unittest.skip ("Skip destructive test")
  def test_dismount (self):
    #
    # Likewise difficult to test because destructive
    #
    pass

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
