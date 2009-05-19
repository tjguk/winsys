from winsys import fs
import os
import filecmp
import shutil
import tempfile
import uuid
import win32file

def _test_parts (path, result, skip_rejoin=False):
  parts = fs.get_parts (path)
  assert (parts == result)
  assert (parts == fs.get_parts (path.replace ("\\", "/")))
  if not skip_rejoin: 
    assert (parts[0] + fs.sep.join (parts[1:]) == path)

#
# get_parts: UNC
#
def test_unc_bare ():
  _test_parts (ur"\\server\share", [u"\\\\server\\share\\", ""], skip_rejoin=True)

def test_unc_root ():
  _test_parts (u"\\\\server\\share\\", [u"\\\\server\\share\\", u""])

def test_unc_directory ():
  _test_parts (u"\\\\server\\share\\test\\", [u"\\\\server\\share\\", u"test", u""])

def test_unc_non_directory ():
  _test_parts (ur"\\server\share\test", [u"\\\\server\\share\\", u"test"])

#
# get_parts: Volume-Drive
#
def test_volume_bare ():
  #
  # No special-casing here...
  #
  _test_parts (ur"\\?\C:", [u"\\\\?\\C:\\", u""], skip_rejoin=True)

def test_volume_bare_leaf ():
  #
  # This one's a bit awkward; maybe we should raise an
  # exception at an invalid filename, but we're not
  # validating anywhere else, so just best-guess it.
  #
  _test_parts (ur"\\?\C:abc.txt", [u"\\\\?\\C:\\", "abc.txt"], skip_rejoin=True)

def test_volume_root ():
  _test_parts (u"\\\\?\\C:\\", [u"\\\\?\\C:\\", u""])

def test_volume_directory ():
  _test_parts (u"\\\\?\\C:\\test\\", [u"\\\\?\\C:\\", u"test", u""])

def test_volume_non_directory ():
  _test_parts (u"\\\\?\\C:\\test\\abc.txt", [u"\\\\?\\C:\\", u"test", u"abc.txt"])

#
# get_parts: Drive
#
def test_drive_bare ():
  _test_parts (u"C:", [u"C:", u""])

def test_drive_bare_leaf ():
  _test_parts (ur"C:abc.txt", [u"C:", u"abc.txt"])

def test_drive_root ():
  _test_parts (u"C:\\", [u"C:\\", u""])

def test_drive_directory ():
  _test_parts (u"C:\\test\\", [u"C:\\", u"test", u""])

def test_drive_non_directory ():
  _test_parts (u"C:\\test\\abc.txt", [u"C:\\", u"test", u"abc.txt"])
  
#
# dumps
#
def test_dump_absolute ():
  fs.filepath (__file__).dump ()

def test_dump_relative ():
  fs.filepath ("@@").dump ()

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
