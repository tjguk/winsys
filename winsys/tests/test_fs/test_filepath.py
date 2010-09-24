import os
import filecmp
import io
import shutil
import tempfile
import unittest
import uuid

import win32file

from winsys import fs
from winsys.tests import utils

def _test_parts (path, result, skip_rejoin=False):
  parts = fs.get_parts (path)
  assert parts == result
  assert parts == fs.get_parts (path.replace ("\\", "/"))
  if not skip_rejoin:
    assert parts[0] + fs.sep.join (parts[1:]) == path

class TestFilepath (unittest.TestCase):

  #
  # get_parts: UNC
  #
  def test_unc_bare (self):
    _test_parts (r"\\server\share", ["\\\\server\\share\\", ""], skip_rejoin=True)

  def test_unc_root (self):
    _test_parts ("\\\\server\\share\\", ["\\\\server\\share\\", ""])

  def test_unc_directory (self):
    _test_parts ("\\\\server\\share\\test\\", ["\\\\server\\share\\", "test"], skip_rejoin=True)

  def test_unc_non_directory (self):
    _test_parts (r"\\server\share\test", ["\\\\server\\share\\", "test"])

  #
  # get_parts: Volume-Drive
  #
  def test_volume_bare (self):
    #
    # No special-casing here...
    #
    _test_parts (r"\\?\C:", ["\\\\?\\C:\\", ""], skip_rejoin=True)

  def test_volume_bare_leaf (self):
    #
    # This one's a bit awkward; maybe we should raise an
    # exception at an invalid filename, but we're not
    # validating anywhere else, so just best-guess it.
    #
    _test_parts (r"\\?\C:abc.txt", ["\\\\?\\C:\\", "abc.txt"], skip_rejoin=True)

  def test_volume_root (self):
    _test_parts ("\\\\?\\C:\\", ["\\\\?\\C:\\", ""])

  def test_volume_directory (self):
    _test_parts ("\\\\?\\C:\\test\\", ["\\\\?\\C:\\", "test"], skip_rejoin=True)

  def test_volume_non_directory (self):
    _test_parts ("\\\\?\\C:\\test\\abc.txt", ["\\\\?\\C:\\", "test", "abc.txt"])

  #
  # get_parts: Drive
  #
  def test_drive_bare (self):
    _test_parts ("C:", ["C:", ""])

  def test_drive_bare_leaf (self):
    _test_parts (r"C:abc.txt", ["C:", "abc.txt"])

  def test_drive_root (self):
    _test_parts ("C:\\", ["C:\\", ""])

  def test_drive_directory (self):
    _test_parts ("C:\\test\\", ["C:\\", "test"], skip_rejoin=True)

  def test_drive_non_directory (self):
    _test_parts ("C:\\test\\abc.txt", ["C:\\", "test", "abc.txt"])

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
  def test_filepath (self):
    test_order = self.test_cases[0][1:]
    for test_case in self.test_cases[1:]:
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
          self.assertEquals (
            result,
            getattr (fp, test_item),
            "Path: %s; Part %s; expected: %s; result: %s" % (path, test_item, result, getattr (fp, test_item))
          )

  #
  # Concatenation
  #
  left = [r"c:\\", r"c:\temp", r"c:\temp\abc.txt", "temp"]
  right = ["abc", r"c:\temp", r"\abc", "abc"]
  def test_add (self):
    for l in self.left:
      for r in self.right:
        self.assertEquals (fs.filepath (l) + r, os.path.join (l, r))

  def test_radd (self):
    for l in self.left:
      for r in self.right:
        self.assertEquals (l + fs.filepath (r), os.path.join (l, r))

  def test_is_relative (self):
    for path, result in [
      ("c:/", False),
      ("c:/temp/abc.txt", False),
      ("temp", True),
      ("c:temp", True),
      (r"\\server\share", False),
      (r"\\server\share\d1", False)
    ]:
      self.assertEquals (fs.filepath (path).is_relative (), result)

  def test_absolute (self):
    for path in ["c:/temp", "temp", "c:temp", r"\\server\share\d1"]:
      self.assertEquals (fs.filepath (path).absolute ().lower (), os.path.abspath (path).lower ())

  #
  # The .changed method returns a version of the filepath
  # with one or more of its components changed. Certain
  # combinations are pointless and raise an exception.
  #
  def test_changed_filename_and_base (self):
    with self.assertRaises (fs.x_fs):
      fs.filepath (".").changed (filename="test.txt", base="test")

  def test_changed_filename_and_ext (self):
    with self.assertRaises (fs.x_fs):
      fs.filepath (".").changed (filename="test.txt", ext=".txt")

  def test_changed_filename_and_infix (self):
    with self.assertRaises (fs.x_fs):
      fs.filepath (".").changed (filename="test.txt", infix="-test-")

  def test_changed_root (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (root="d:\\"), "d:\\temp\\abc.txt")

  def test_changed_dirname (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (dirname="temp2"), "c:\\temp2\\abc.txt")

  def test_changed_filename (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (filename="def.ghi"), "c:\\temp\\def.ghi")

  def test_changed_base (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (base="def"), "c:\\temp\\def.txt")

  def test_changed_infix (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (infix=".infix"), "c:\\temp\\abc.infix.txt")

  def test_changed_ext (self):
    self.assertEquals (fs.filepath ("c:\\temp\\abc.txt").changed (ext=".ext"), "c:\\temp\\abc.ext")

  #
  # dumps
  #
  def test_dump_absolute (self):
    with utils.fake_stdout ():
      fs.filepath (__file__).dump ()

  def test_dump_relative (self):
    with utils.fake_stdout ():
      fs.filepath ("@@").dump ()

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
