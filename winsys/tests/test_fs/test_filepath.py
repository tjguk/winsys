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
# Concatenation
#
left = [r"c:\\", r"c:\temp", r"c:\temp\abc.txt", "temp"]
right = ["abc", r"c:\temp", r"\abc", "abc"]
def test_add ():
  for l in left:
    for r in right:
      assert_equals (fs.filepath (l) + r, os.path.join (l, r))

def test_radd ():
  for l in left:
    for r in right:
      assert_equals (l + fs.filepath (r), os.path.join (l, r))

def test_is_relative ():
  for path, result in [
    ("c:/", False),
    ("c:/temp/abc.txt", False),
    ("temp", True),
    ("c:temp", True),
    (r"\\server\share", False),
    (r"\\server\share\d1", False)
  ]:
    assert_equals (fs.filepath (path).is_relative (), result)

def test_absolute ():
  for path in ["c:/temp", "temp", "c:temp", r"\\server\share\d1"]:
    assert_equals (fs.filepath (path).absolute ().lower (), os.path.abspath (path).lower ())

#
# The .changed method returns a version of the filepath
# with one or more of its components changed. Certain
# combinations are pointless and raise an exception.
#
@raises (fs.x_fs)
def test_changed_filename_and_base ():
  fs.filepath (".").changed (filename="test.txt", base="test")

@raises (fs.x_fs)
def test_changed_filename_and_ext ():
  fs.filepath (".").changed (filename="test.txt", ext=".txt")

@raises (fs.x_fs)
def test_changed_filename_and_infix ():
  fs.filepath (".").changed (filename="test.txt", infix="-test-")

def test_changed_root ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (root="d:\\"), "d:\\temp\\abc.txt")

def test_changed_dirname ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (dirname="temp2"), "c:\\temp2\\abc.txt")

def test_changed_filename ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (filename="def.ghi"), "c:\\temp\\def.ghi")

def test_changed_base ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (base="def"), "c:\\temp\\def.txt")

def test_changed_infix ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (infix=".infix"), "c:\\temp\\abc.infix.txt")

def test_changed_ext ():
  assert_equals (fs.filepath ("c:\\temp\\abc.txt").changed (ext=".ext"), "c:\\temp\\abc.ext")

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
  if sys.stdout.isatty (): raw_input ("Press enter...")
