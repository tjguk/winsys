import os, sys
import struct
import tempfile
import unittest2 as unittest

import win32api
import win32file

from winsys import fs

class TestVolume (unittest.TestCase):

  @staticmethod
  def get_info (volume):
    return win32api.GetVolumeInformation (volume)

  @staticmethod
  def get_volume ():
    return win32file.GetVolumeNameForVolumeMountPoint (sys.executable[:3])

  def test_name (self):
    volume = self.get_volume ()
    v = fs.Volume (volume)
    self.assertEquals (v.name, volume)

  def test_label (self):
    volume = self.get_volume ()
    info = self.get_info (volume)
    self.assertEquals (fs.Volume (volume).label, info[0])

  def test_serial_number (self):
    volume = self.get_volume ()
    info = self.get_info (volume)
    #
    # Convert signed to unsigned number
    #
    value, = struct.unpack ("L", struct.pack ("l", info[1]))
    self.assertEquals (fs.Volume (volume).serial_number, value)

  def test_maximum_component_length (self):
    volume = self.get_volume ()
    info = self.get_info (volume)
    self.assertEquals (fs.Volume (volume).maximum_component_length, info[2])

  def test_flags (self):
    volume = self.get_volume ()
    info = self.get_info (volume)
    self.assertEquals (fs.Volume (volume).flags.flags, info[3])

  def test_file_system_name (self):
    volume = self.get_volume ()
    info = self.get_info (volume)
    self.assertEquals (fs.Volume (volume).file_system_name, info[4])

  def test_mounts (self):
    volume = self.get_volume ()
    self.assertEquals (
      list (fs.Volume (volume).mounts),
      [path.lower () for path in win32file.GetVolumePathNamesForVolumeName (volume)]
    )

  @unittest.skip ("Difficult to test")
  def test_mount (self):
    #
    # Difficult to test because it's not possible
    # to mount a volume on two drive letters simultaneously.
    # Try to find something unimportant, like a CDROM, and
    # dismount it before remounting it.
    #
    pass

  @unittest.skip ("Destructive test")
  def test_dismount (self):
    #
    # Likewise difficult to test because destructive
    #
    pass

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
