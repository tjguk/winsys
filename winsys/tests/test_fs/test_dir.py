from winsys import fs
import os, sys
import glob
import tempfile
import threading
import uuid
import unittest

import win32file

from winsys.tests.test_fs import utils

FILE_ATTRIBUTE_ENCRYPTED = 0x00004000

class TestDir (unittest.TestCase):

  def setUp (self):
    self.filenames = ["%d" % i for i in range (5)]
    utils.mktemp ()
    for filename in self.filenames:
      open (os.path.join (utils.TEST_ROOT, filename), "w").close ()
    os.mkdir (os.path.join (utils.TEST_ROOT, "d"))
    for filename in self.filenames:
      open (os.path.join (utils.TEST_ROOT, "d", filename), "w").close ()
    os.mkdir (os.path.join (utils.TEST_ROOT, "empty"))

  def tearDown (self):
    utils.rmtemp ()

  def test_unicode (self):
    path = str (os.path.dirname (sys.executable)).rstrip (fs.sep) + fs.sep
    self.assertEquals (path, fs.Dir (path))

  def test_compress (self):
    filepath = utils.TEST_ROOT

    self.assertFalse (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).compress ()

    self.assertTrue (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).uncompress ()

    self.assertFalse (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  def test_compress_not_contents (self):
    filepath = utils.TEST_ROOT

    self.assertFalse (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).compress (apply_to_contents=False)

    self.assertTrue (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  def test_uncompress_not_contents (self):
    filepath = utils.TEST_ROOT

    fs.Dir (filepath).compress ()
    self.assertTrue (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

    fs.Dir (filepath).uncompress (apply_to_contents=False)

    self.assertFalse (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  @unittest.skipUnless (utils.can_encrypt (), "No certificate available")
  def test_encrypt (self):
    filepath = utils.TEST_ROOT

    self.assertFalse (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).encrypt ()

    self.assertTrue (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).unencrypt ()

    self.assertFalse (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  @unittest.skipUnless (utils.can_encrypt (), "No certificate available")
  def test_encrypt_not_contents (self):
    filepath = utils.TEST_ROOT

    self.assertFalse (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).encrypt (apply_to_contents=False)

    self.assertTrue (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertFalse (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  @unittest.skipUnless (utils.can_encrypt (), "No certificate available")
  def test_unencrypt_not_contents (self):
    filepath = utils.TEST_ROOT

    fs.Dir (filepath).encrypt ()
    self.assertTrue (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

    fs.Dir (filepath).unencrypt (apply_to_contents=False)

    self.assertFalse (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
    for filename in self.filenames:
      self.assertTrue (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  def test_create (self):
    filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)
    self.assertFalse (os.path.exists (filepath))
    fs.dir (filepath).create ()
    self.assertTrue (os.path.exists (filepath))
    self.assertTrue (os.path.isdir (filepath))

  def test_create_already_exists_dir (self):
    #
    # If the dir already exists, create will succeed silently
    # and will return the normalised path of the dir.
    #
    filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)
    os.mkdir (filepath)
    self.assertTrue (os.path.isdir (filepath))
    d = fs.dir (filepath)
    self.assertEquals (fs.normalised (d), fs.normalised (d.create ()))

  def test_create_already_exists_not_dir (self):
    with self.assertRaises (fs.x_fs):
      #
      # If the name is already used by a file, create will raise x_fs
      #
      filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)
      open (filepath, "w").close ()
      self.assertTrue (os.path.isfile (filepath))
      fs.dir (filepath).create ()

  @unittest.skip ("Skipping this test")
  def test_dir_create_with_security (self):
    pass

  def test_entries (self):
    filepath = utils.TEST_ROOT
    self.assertEquals (
      set (fs.dir (filepath).entries ()),
      utils.files_in (filepath) | utils.dirs_in (filepath)
    )

  def test_file (self):
    filepath = utils.TEST_ROOT
    self.assertEquals (fs.dir (filepath).file ("1"), os.path.join (filepath, "1"))

  def test_dir (self):
    filepath = utils.TEST_ROOT
    self.assertEquals (fs.dir (filepath).dir ("d"), os.path.join (filepath, "d\\"))

  def test_dirs (self):
    filepath = utils.TEST_ROOT
    self.assertEquals (
      set (fs.dir (filepath).dirs ()),
      utils.dirs_in (filepath)
    )

  def test_walk (self):
    filepath = utils.TEST_ROOT
    walker = fs.dir (filepath).walk ()
    dirpath, dirs, files = next (walker)
    self.assertEquals (dirpath, filepath + "\\")
    self.assertEquals (set (dirs), utils.dirs_in (filepath))
    self.assertEquals (set (files), utils.files_in (filepath))

    filepath = os.path.join (filepath, "d")
    dirpath, dirs, files = next (walker)
    self.assertEquals (dirpath, filepath + "\\")
    self.assertEquals (set (dirs), utils.dirs_in (filepath))
    self.assertEquals (set (files), utils.files_in (filepath))

  def test_flat (self):
    filepath = utils.TEST_ROOT
    self.assertEquals (
      set (fs.dir (filepath).flat ()),
      utils.files_in (filepath) | utils.files_in (os.path.join (filepath, "d"))
    )

  def test_flat_with_dirs (self):
    filepath = utils.TEST_ROOT
    filepath2 = os.path.join (filepath, "d")
    self.assertEquals (
      set (fs.dir (filepath).flat (includedirs=True)),
      utils.dirs_in (filepath) | utils.files_in (filepath) | utils.dirs_in (filepath2) | utils.files_in (filepath2)
    )

  def test_dir_copy_to_new_dir (self):
    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    source = os.path.join (utils.TEST_ROOT, source_name)
    target = os.path.join (utils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    self.assertTrue (os.path.isdir (source))
    self.assertFalse (os.path.isdir (target))
    fs.copy (source, target)
    self.assertTrue (*utils.dirs_are_equal (source, target))

  def test_dir_copy_to_existing_dir (self):
    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    source = os.path.join (utils.TEST_ROOT, source_name)
    target = os.path.join (utils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    os.mkdir (target)
    self.assertTrue (os.path.isdir (source))
    self.assertTrue (os.path.isdir (target))
    fs.copy (source, target)
    self.assertTrue (*utils.dirs_are_equal (source, target))

  def test_dir_copy_with_callback (self):
    callback_result = []
    def _callback (total_size, size_so_far, data):
      callback_result.append ((total_size, size_so_far, data))

    source_name = uuid.uuid1 ().hex
    target_name = uuid.uuid1 ().hex
    callback_data = uuid.uuid1 ().hex
    source = os.path.join (utils.TEST_ROOT, source_name)
    target = os.path.join (utils.TEST_ROOT, target_name)
    os.mkdir (source)
    for i in range (10):
      open (os.path.join (source, "%d.dat" % i), "w").close ()
    self.assertTrue (os.path.isdir (source))
    self.assertFalse (os.path.isdir (target))
    fs.copy (source, target, _callback, callback_data)
    self.assertTrue (*utils.dirs_are_equal (source, target))
    self.assertEquals (len (callback_result), 10)
    self.assertEquals (callback_result, [(0, 0, callback_data) for i in range (10)])

  def test_delete (self):
    filepath = os.path.join (utils.TEST_ROOT, "empty")
    self.assertTrue (os.path.exists (filepath))
    fs.Dir (filepath).delete ()
    self.assertFalse (os.path.exists (filepath))

  def test_delete_recursive (self):
    filepath = os.path.join (utils.TEST_ROOT, "d")
    self.assertTrue (os.path.exists (filepath))
    self.assertTrue (utils.files_in (filepath))
    fs.Dir (filepath).delete (recursive=True)
    self.assertFalse (os.path.exists (filepath))

  def test_watch (self):
    filepath = utils.TEST_ROOT
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
    self.assertEquals (next (watcher), (fs.FILE_ACTION.REMOVED, removed_filename, None))
    self.assertEquals (next (watcher), (fs.FILE_ACTION.ADDED, None, added_filename))
    self.assertEquals (next (watcher), (fs.FILE_ACTION.RENAMED_NEW_NAME, old_filename, new_filename))
    t.join ()

  def test_zip (self):
    import zipfile
    filepath = utils.TEST_ROOT
    zipped = fs.dir (filepath).zip ()
    unzip_filepath = os.path.join (utils.TEST_ROOT2)
    os.mkdir (unzip_filepath)
    zipfile.ZipFile (zipped).extractall (unzip_filepath)
    self.assertEquals (
      set (f.relative_to (filepath) for f in fs.flat (filepath)),
      set (f.relative_to (unzip_filepath) for f in fs.flat (unzip_filepath))
    )

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
