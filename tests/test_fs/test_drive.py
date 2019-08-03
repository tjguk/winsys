# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys
import tempfile
from winsys._compat import unittest

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
      self.assertEqual (fs.drive (name).name, "c:\\")
      self.assertEqual (fs.drive (name.lower ()).name, "c:\\")

  def test_DriveType (self):
    self.assertEqual (fs.drive ("C:").type, win32file.GetDriveTypeW ("C:"))

  def test_DriveRoot (self):
    self.assertEqual (fs.drive ("C:").root, fs.dir ("C:\\"))

  def test_volume (self):
    self.assertEqual (fs.drive ("C:").volume.name, win32file.GetVolumeNameForVolumeMountPoint ("C:\\"))

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
