# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from winsys import fs
import os, sys
import glob
import tempfile
import threading
import uuid
from winsys._compat import unittest

import win32file

from . import utils as fsutils

FILE_ATTRIBUTE_ENCRYPTED = 0x00004000

class TestDir (unittest.TestCase):

  def setUp (self):
    self.filenames = ["%d" % i for i in range (5)]
    fsutils.mktemp ()
    for filename in self.filenames:
      open (os.path.join (fsutils.TEST_ROOT, filename), "w").close ()
    os.mkdir (os.path.join (fsutils.TEST_ROOT, "d"))
    for filename in self.filenames:
      open (os.path.join (fsutils.TEST_ROOT, "d", filename), "w").close ()
    os.mkdir (os.path.join (fsutils.TEST_ROOT, "empty"))

  def tearDown (self):
    fsutils.rmtemp ()

  def test_unicode (self):
    path = str (os.path.dirname (sys.executable)).rstrip (fs.sep) + fs.sep
    self.assertEqual (path, fs.Dir (path))

  def test_compress (self):
    filepath = fsutils.TEST_ROOT

    self.assertFalse (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).compress ()

    self.assertTrue (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).uncompress ()

    self.assertFalse (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  def test_compress_not_contents (self):
    filepath = fsutils.TEST_ROOT

    self.assertFalse (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).compress (apply_to_contents=False)

    self.assertTrue (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  def test_uncompress_not_contents (self):
    filepath = fsutils.TEST_ROOT

    fs.Dir (filepath).compress ()
    self.assertTrue (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).uncompress (apply_to_contents=False)

    self.assertFalse (fsutils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  @unittest.skipUnless (fsutils.can_encrypt (), "No certificate available")
  def test_encrypt (self):
    filepath = fsutils.TEST_ROOT

    self.assertFalse (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).encrypt ()

    self.assertTrue (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).unencrypt ()

    self.assertFalse (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  @unittest.skipUnless (fsutils.can_encrypt (), "No certificate available")
  def test_encrypt_not_contents (self):
    filepath = fsutils.TEST_ROOT

    self.assertFalse (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).encrypt (apply_to_contents=False)

    self.assertTrue (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  @unittest.skipUnless (fsutils.can_encrypt (), "No certificate available")
  def test_unencrypt_not_contents (self):
    filepath = fsutils.TEST_ROOT

    fs.Dir (filepath).encrypt ()
    self.assertTrue (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).unencrypt (apply_to_contents=False)

    self.assertFalse (fsutils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (fsutils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  def test_create (self):
    filepath = os.path.join (fsutils.TEST_ROOT, uuid.uuid1 ().hex)
    self.assertFalse (os.path.exists (filepath))
    fs.dir (filepath).create ()
    self.assertTrue (os.path.exists (filepath))
    self.assertTrue (os.path.isdir (filepath))

  def test_create_already_exists_dir (self):
    #
    # If the dir already exists, create will succeed silently
    # and will return the normalised path of the dir.
    #
    filepath = os.path.join (fsutils.TEST_ROOT, uuid.uuid1 ().hex)
    os.mkdir (filepath)
    self.assertTrue (os.path.isdir (filepath))
    d = fs.dir (filepath)
    self.assertEqual (fs.normalised (d), fs.normalised (d.create ()))

  def test_create_already_exists_not_dir (self):
    with self.assertRaises (fs.x_fs):
      #
      # If the name is already used by a file, create will raise x_fs
      #
      filepath = os.path.join (fsutils.TEST_ROOT, uuid.uuid1 ().hex)
      open (filepath, "w").close ()
      self.assertTrue (os.path.isfile (filepath))
      fs.dir (filepath).create ()

  @unittest.skip ("Skipping this test")
  def test_dir_create_with_security (self):
    pass

  def test_entries (self):
    filepath = fsutils.TEST_ROOT
    self.assertEqual (
      set(str(i) for i in fs.dir(filepath).entries()),
      fsutils.files_in(filepath) | fsutils.dirs_in(filepath)
    )

  def test_file (self):
    filepath = fsutils.TEST_ROOT
    self.assertEqual (fs.dir (filepath).file ("1"), os.path.join (filepath, "1"))

  def test_dir (self):
    filepath = fsutils.TEST_ROOT
    self.assertEqual (fs.dir (filepath).dir ("d"), os.path.join (filepath, "d\\"))

  def test_dirs (self):
    filepath = fsutils.TEST_ROOT
    self.assertEqual (
      set(str(i) for i in fs.dir(filepath).dirs()),
      fsutils.dirs_in(filepath)
    )

  def test_walk (self):
    filepath = fsutils.TEST_ROOT
    walker = fs.dir (filepath).walk ()
    dirpath, dirs, files = next (walker)
    self.assertEqual(dirpath, filepath + "\\")
    self.assertEqual(set(str(d) for d in dirs), fsutils.dirs_in(filepath))
    self.assertEqual(set(str(f) for f in files), fsutils.files_in(filepath))

    filepath = os.path.join (filepath, "d")
    dirpath, dirs, files = next (walker)
    self.assertEqual(dirpath, filepath + "\\")
    self.assertEqual(set(str(d) for d in dirs), fsutils.dirs_in(filepath))
    self.assertEqual(set(str(f) for f in files), fsutils.files_in(filepath))

  def test_flat (self):
    filepath = fsutils.TEST_ROOT
    self.assertEqual (
      set(str(i) for i in fs.dir(filepath).flat()),
      fsutils.files_in(filepath) | fsutils.files_in(os.path.join(filepath, "d"))
    )

  def test_flat_with_dirs (self):
    filepath = fsutils.TEST_ROOT
    filepath2 = os.path.join(filepath, "d")
    self.assertEqual (
      set (str(i) for i in fs.dir(filepath).flat(includedirs=True)),
      fsutils.dirs_in(filepath) | fsutils.files_in(filepath) | fsutils.dirs_in(filepath2) | fsutils.files_in(filepath2)
    )

  def test_dir_copy_to_new_dir (self):
    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    source = os.path.join (fsutils.TEST_ROOT, source_name)
    target = os.path.join (fsutils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    self.assertTrue (os.path.isdir (source))
    self.assertFalse (os.path.isdir (target))
    fs.copy (source, target)
    self.assertTrue (*fsutils.dirs_are_equal (source, target))

  def test_dir_copy_to_existing_dir (self):
    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    source = os.path.join (fsutils.TEST_ROOT, source_name)
    target = os.path.join (fsutils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    os.mkdir (target)
    self.assertTrue (os.path.isdir (source))
    self.assertTrue (os.path.isdir (target))
    fs.copy (source, target)
    self.assertTrue (*fsutils.dirs_are_equal (source, target))

  def test_dir_copy_with_callback (self):
    callback_result = []
    def _callback (total_size, size_so_far, data):
      callback_result.append ((total_size, size_so_far, data))

    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    callback_data = uuid.uuid1 ().hex
    source = os.path.join (fsutils.TEST_ROOT, source_name)
    target = os.path.join (fsutils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    self.assertTrue (os.path.isdir (source))
    self.assertFalse (os.path.isdir (target))
    fs.copy (source, target, _callback, callback_data)
    self.assertTrue (*fsutils.dirs_are_equal (source, target))
    self.assertEqual (len (callback_result), 10)
    self.assertEqual (callback_result, [(0, 0, callback_data) for i in range (10)])

  def test_delete (self):
    filepath = os.path.join (fsutils.TEST_ROOT, "empty")
    self.assertTrue (os.path.exists (filepath))
    fs.Dir (filepath).delete ()
    self.assertFalse (os.path.exists (filepath))

  def test_delete_recursive (self):
    filepath = os.path.join (fsutils.TEST_ROOT, "d")
    self.assertTrue (os.path.exists (filepath))
    self.assertTrue (fsutils.files_in (filepath))
    fs.Dir (filepath).delete (recursive=True)
    self.assertFalse (os.path.exists (filepath))

  def test_watch (self):
    filepath = fsutils.TEST_ROOT
    removed_filename = os.path.join (filepath, "1")
    added_filename = os.path.join (filepath, uuid.uuid1 ().hex)
    old_filename = os.path.join (filepath, "2")
    new_filename = os.path.join (filepath, uuid.uuid1 ().hex)
    def _change_dir ():
      os.remove (removed_filename)
      open (added_filename, "w").close ()
      os.rename (old_filename, new_filename)

    watcher = fs.dir (filepath).watch ()
    t = threading.Timer (0.5, _change_dir)
    t.start ()
    self.assertEqual (next (watcher), (fs.FILE_ACTION.REMOVED, removed_filename, None))
    self.assertEqual (next (watcher), (fs.FILE_ACTION.ADDED, None, added_filename))
    self.assertEqual (next (watcher), (fs.FILE_ACTION.RENAMED_NEW_NAME, old_filename, new_filename))
    t.join ()

  def test_zip (self):
    import zipfile
    filepath = fsutils.TEST_ROOT
    zipped = fs.dir (filepath).zip ()
    unzip_filepath = os.path.join (fsutils.TEST_ROOT2)
    os.mkdir (unzip_filepath)
    zipfile.ZipFile (zipped).extractall (unzip_filepath)
    self.assertEqual (
      set (f.relative_to (filepath) for f in fs.flat (filepath)),
      set (f.relative_to (unzip_filepath) for f in fs.flat (unzip_filepath))
    )

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
