from winsys import fs
import os
import filecmp
import shutil
import tempfile
import uuid
import win32file

from nose.tools import *

def _test_parts (path, result, skip_rejoin=False):
  parts = fs.get_parts (path)
  assert parts == result
  assert parts == fs.get_parts (path.replace ("\\", "/"))
  if not skip_rejoin: 
    assert parts[0] + fs.sep.join (parts[1:]) == path

#
# get_parts: UNC
#
def test_unc_bare ():
  _test_parts (ur"\\server\share", [u"\\\\server\\share\\", ""], skip_rejoin=True)

def test_unc_root ():
  _test_parts (u"\\\\server\\share\\", [u"\\\\server\\share\\", u""])

def test_unc_directory ():
  _test_parts (u"\\\\server\\share\\test\\", [u"\\\\server\\share\\", u"test"], skip_rejoin=True)

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
  _test_parts (u"\\\\?\\C:\\test\\", [u"\\\\?\\C:\\", u"test"], skip_rejoin=True)

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
  _test_parts (u"C:\\test\\", [u"C:\\", u"test"], skip_rejoin=True)

def test_drive_non_directory ():
  _test_parts (u"C:\\test\\abc.txt", [u"C:\\", u"test", u"abc.txt"])

#
# filepath
#
test_cases = [line.split () for line in """
  path                root       filename  name      dirname   path        parent      base   ext
  \\\\a\\b\\c\\d.txt  \\\\a\\b\\ d.txt     d.txt     c         \\\\a\\b\\c \\\\a\\b\\c d     .txt
  c:\\boot.ini        c:\\       boot.ini  boot.ini  _         c:\\        c:\\        boot  .ini
  boot.ini            _          boot.ini  boot.ini  _         _           x_fs        boot  .ini
  c:\\t               c:\\       t         t         _         c:\\        c:\\        t     _
  c:\\t\\             c:\\       t         t         _         c:\\        c:\\        t     _
  c:\\t\\a.txt        c:\\       a.txt     a.txt     t         c:\\t       c:\\t       a     .txt
  c:a.txt             c:         a.txt     a.txt     _         c:          x_fs        a     .txt
  a.txt               _          a.txt     a.txt     _         _           x_fs        a     .txt
""".splitlines () if line.strip ()]
def test_filepath ():
  test_order = test_cases[0][1:]
  for test_case in test_cases[1:]:
    path, rest = test_case[0], test_case[1:]
    fp = fs.filepath (path)
    for n, test_item in enumerate (test_order):
      result = rest[n]
      if result.startswith ("x_"):
        exc = getattr (fs, result)
        try:
          getattr (fp, test_item)
        except exc:
          pass
        else:
          raise RuntimeError (
            "Path: %s; Part: %s; expected exception %s" % (path, test_item, result)
          )
      else:
        if result == "_":
          result = ""
        assert_equals (
          result, 
          getattr (fp, test_item), 
          "Path: %s; Part %s; expected: %s; result: %s" % (path, test_item, result, getattr (fp, test_item))
        )

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
