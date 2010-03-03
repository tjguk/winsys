from winsys import fs
import os, sys
import glob
import tempfile
import threading
import uuid
import win32file
import utils

from nose.tools import *
from nose.plugins import skip

FILE_ATTRIBUTE_ENCRYPTED = 0x00004000

filenames = ["%d" % i for i in range (5)]
def fn_setup ():
  utils.mktemp ()
  for filename in filenames:
    open (os.path.join (utils.TEST_ROOT, filename), "w").close ()
  os.mkdir (os.path.join (utils.TEST_ROOT, "d"))
  for filename in filenames:
    open (os.path.join (utils.TEST_ROOT, "d", filename), "w").close ()
  os.mkdir (os.path.join (utils.TEST_ROOT, "empty"))
  
def fn_teardown ():
  utils.rmtemp ()

@with_setup (fn_setup, fn_teardown)
def test_unicode ():
  path = unicode (os.path.dirname (sys.executable)).rstrip (fs.sep) + fs.sep
  assert_equal (path, fs.Dir (path))
  
@with_setup (fn_setup, fn_teardown)
def test_compress ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  
  fs.Dir (filepath).compress ()

  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  fs.Dir (filepath).uncompress ()

  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

@with_setup (fn_setup, fn_teardown)
def test_compress_not_contents ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  
  fs.Dir (filepath).compress (apply_to_contents=False)

  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

@with_setup (fn_setup, fn_teardown)
def test_uncompress_not_contents ():
  filepath = utils.TEST_ROOT
  
  fs.Dir (filepath).compress ()
  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

  fs.Dir (filepath).uncompress (apply_to_contents=False)

  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

@with_setup (fn_setup, fn_teardown)
def test_encrypt ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)
  
  fs.Dir (filepath).encrypt ()

  assert_true (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  fs.Dir (filepath).unencrypt ()

  assert_false (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

@with_setup (fn_setup, fn_teardown)
def test_encrypt_not_contents ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)
  
  fs.Dir (filepath).encrypt (apply_to_contents=False)

  assert_true (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

@with_setup (fn_setup, fn_teardown)
def test_unencrypt_not_contents ():
  filepath = utils.TEST_ROOT
  
  fs.Dir (filepath).encrypt ()
  assert_true (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

  fs.Dir (filepath).unencrypt (apply_to_contents=False)

  assert_false (utils.attributes (filepath) & FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & FILE_ATTRIBUTE_ENCRYPTED)

@with_setup (fn_setup, fn_teardown)
def test_create ():
  filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)  
  assert_false (os.path.exists (filepath))
  fs.dir (filepath).create ()
  assert_true (os.path.exists (filepath))
  assert_true (os.path.isdir (filepath))

@with_setup (fn_setup, fn_teardown)
def test_create_already_exists_dir ():
  #
  # If the dir already exists, create will succeed silently
  # and will return the normalised path of the dir.
  #
  filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)
  os.mkdir (filepath)
  assert_true (os.path.isdir (filepath))
  d = fs.dir (filepath)
  assert_equals (fs.normalised (d), fs.normalised (d.create ()))

@raises (fs.x_fs)
@with_setup (fn_setup, fn_teardown)
def test_create_already_exists_not_dir ():
  #
  # If the name is already used by a file, create will raise x_fs
  #
  filepath = os.path.join (utils.TEST_ROOT, uuid.uuid1 ().hex)
  open (filepath, "w").close ()
  assert_true (os.path.isfile (filepath))
  fs.dir (filepath).create ()

@with_setup (fn_setup, fn_teardown)
def test_dir_create_with_security ():
  raise skip.SkipTest

@with_setup (fn_setup, fn_teardown)
def test_entries ():
  filepath = utils.TEST_ROOT
  assert_equals (
    set (fs.dir (filepath).entries ()),
    utils.files_in (filepath) | utils.dirs_in (filepath)
  )
  
@with_setup (fn_setup, fn_teardown)
def test_file ():
  filepath = utils.TEST_ROOT
  assert_equals (fs.dir (filepath).file ("1"), os.path.join (filepath, "1"))

@with_setup (fn_setup, fn_teardown)
def test_dir ():
  filepath = utils.TEST_ROOT
  assert_equals (fs.dir (filepath).dir ("d"), os.path.join (filepath, "d\\"))

@with_setup (fn_setup, fn_teardown)
def test_dirs ():
  filepath = utils.TEST_ROOT
  assert_equals (
    set (fs.dir (filepath).dirs ()), 
    utils.dirs_in (filepath)
  )

@with_setup (fn_setup, fn_teardown)
def test_walk ():
  filepath = utils.TEST_ROOT
  walker = fs.dir (filepath).walk ()
  dirpath, dirs, files = walker.next ()
  assert_equals (dirpath, filepath + "\\")
  assert_equals (set (dirs), utils.dirs_in (filepath))
  assert_equals (set (files), utils.files_in (filepath))
  
  filepath = os.path.join (filepath, "d")
  dirpath, dirs, files = walker.next ()
  assert_equals (dirpath, filepath + "\\")
  assert_equals (set (dirs), utils.dirs_in (filepath))
  assert_equals (set (files), utils.files_in (filepath))
  
@with_setup (fn_setup, fn_teardown)
def test_flat ():
  filepath = utils.TEST_ROOT
  assert_equals (
    set (fs.dir (filepath).flat ()), 
    utils.files_in (filepath) | utils.files_in (os.path.join (filepath, "d"))
  )

@with_setup (fn_setup, fn_teardown)
def test_flat_with_dirs ():
  filepath = utils.TEST_ROOT
  filepath2 = os.path.join (filepath, "d")
  assert_equals (
    set (fs.dir (filepath).flat (includedirs=True)), 
    utils.dirs_in (filepath) | utils.files_in (filepath) | utils.dirs_in (filepath2) | utils.files_in (filepath2)
  )

@with_setup (fn_setup, fn_teardown)
def test_dir_copy_to_new_dir ():
  source_name = uuid.uuid1 ().hex
  target_name = uuid.uuid1 ().hex
  source = os.path.join (utils.TEST_ROOT, source_name)
  target = os.path.join (utils.TEST_ROOT, target_name)
  os.mkdir (source)
  for i in range (10):
    open (os.path.join (source, "%d.dat" % i), "w").close ()
  assert_true (os.path.isdir (source))
  assert_false (os.path.isdir (target))
  fs.copy (source, target)
  assert_true (utils.dirs_are_equal (source, target))
  
@with_setup (fn_setup, fn_teardown)
def test_dir_copy_to_existing_dir ():
  source_name = uuid.uuid1 ().hex
  target_name = uuid.uuid1 ().hex
  source = os.path.join (utils.TEST_ROOT, source_name)
  target = os.path.join (utils.TEST_ROOT, target_name)
  os.mkdir (source)
  for i in range (10):
    open (os.path.join (source, "%d.dat" % i), "w").close ()
  os.mkdir (target)
  assert_true (os.path.isdir (source))
  assert_true (os.path.isdir (target))
  fs.copy (source, target)
  assert_true (utils.dirs_are_equal (source, target))

@with_setup (fn_setup, fn_teardown)
def test_dir_copy_with_callback ():
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
  assert_true (os.path.isdir (source))
  assert_false (os.path.isdir (target))
  fs.copy (source, target, _callback, callback_data)
  assert_true (utils.dirs_are_equal (source, target))
  assert_equals (len (callback_result), 10)
  assert_equals (callback_result, [(0, 0, callback_data) for i in range (10)])

@with_setup (fn_setup, fn_teardown)
def test_delete ():
  filepath = os.path.join (utils.TEST_ROOT, "empty")
  assert_true (os.path.exists (filepath))
  fs.Dir (filepath).delete ()
  assert_false (os.path.exists (filepath))

@with_setup (fn_setup, fn_teardown)
def test_delete_recursive ():
  filepath = os.path.join (utils.TEST_ROOT, "d")
  assert_true (os.path.exists (filepath))
  assert_true (utils.files_in (filepath))
  fs.Dir (filepath).delete (recursive=True)
  assert_false (os.path.exists (filepath))

@with_setup (fn_setup, fn_teardown)
def test_watch ():
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
  assert_equals (watcher.next (), (fs.FILE_ACTION.REMOVED, removed_filename, None))
  assert_equals (watcher.next (), (fs.FILE_ACTION.ADDED, None, added_filename))
  assert_equals (watcher.next (), (fs.FILE_ACTION.RENAMED_NEW_NAME, old_filename, new_filename))
  t.join ()

@with_setup (fn_setup, fn_teardown)
def test_zip ():
  import zipfile
  filepath = utils.TEST_ROOT
  zipped = fs.dir (filepath).zip ()
  unzip_filepath = os.path.join (filepath, "unzip")
  os.mkdir (unzip_filepath)
  zipfile.ZipFile (zipped).extractall (unzip_filepath)
  print utils.files_in (filepath)
  print utils.files_in (unzip_filepath)
  print utils.dirs_in (filepath)
  print utils.dirs_in (unzip_filepath)
  assert_true (utils.dirs_are_equal (filepath, unzip_filepath))

def test_dir_create_with_security ():
  raise skip.SkipTest

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
