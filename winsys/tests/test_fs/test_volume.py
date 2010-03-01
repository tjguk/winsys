import os, sys
import struct
import tempfile
import win32api
import win32file

from winsys import fs

from nose.tools import *
from nose.plugins import skip

def get_info (volume):
  return win32api.GetVolumeInformation (volume)

def get_volume ():
  return win32file.GetVolumeNameForVolumeMountPoint (sys.executable[:3])

def test_name ():
  volume = get_volume ()
  v = fs.Volume (volume)
  assert_equals (v.name, volume)

def test_label ():
  volume = get_volume ()
  info = get_info (volume)
  assert_equals (fs.Volume (volume).label, info[0])

def test_serial_number ():
  volume = get_volume ()
  info = get_info (volume)
  #
  # Convert signed to unsigned number
  #
  value, = struct.unpack ("L", struct.pack ("l", info[1]))
  assert_equals (fs.Volume (volume).serial_number, value)

def test_maximum_component_length ():
  volume = get_volume ()
  info = get_info (volume)
  assert_equals (fs.Volume (volume).maximum_component_length, info[2])

def test_flags ():
  volume = get_volume ()
  info = get_info (volume)
  assert_equals (fs.Volume (volume).flags.flags, info[3])

def test_file_system_name ():
  volume = get_volume ()
  info = get_info (volume)
  assert_equals (fs.Volume (volume).file_system_name, info[4])

def test_mounts ():
  volume = get_volume ()
  assert_equals (
    list (fs.Volume (volume).mounts),
    [path.lower () for path in win32file.GetVolumePathNamesForVolumeName (volume)]
  )

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
