from winsys import fs
import os, sys
import glob
import tempfile
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
    list (f.rstrip ("\\") for f in fs.dir (filepath).entries ()), 
    glob.glob (os.path.join (filepath, "*"))
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
    list (fs.dir (filepath).dirs ()), 
    [g + "\\" for g in glob.glob (os.path.join (filepath, "*")) if os.path.isdir (g)]
  )

@with_setup (fn_setup, fn_teardown)
def test_walk ():
  filepath = utils.TEST_ROOT
  walker = fs.dir (filepath).walk ()
  dirpath, dirs, files = walker.next ()
  assert_equals (dirpath, filepath + "\\")
  assert_equals (dirs, [os.path.join (filepath, "d\\")])
  assert_equals (files, [os.path.join (filepath, f) for f in filenames])
  dirpath, dirs, files = walker.next ()
  assert_equals (dirpath, os.path.join (filepath, "d\\"))
  assert_equals (dirs, [])
  assert_equals (files, [os.path.join (filepath, "d", f) for f in filenames])
  

@with_setup (fn_setup, fn_teardown)
def test_dir_copy_to_new_dir ():
  source_name = uuid.uuid1 ().hex
  target_name = uuid.uuid1 ().hex
  source = os.path.join (utils.TEST_ROOT, source_name)
  target = os.path.join (utils.TEST_ROOT, target_name)
  os.mkdir (source)
  assert_true (os.path.isdir (source))
  assert_false (os.path.isdir (target))
  fs.copy (source, target)
  assert_true (utils.dirs_are_equal (source, target))
  
def test_dir_create_with_security ():
  raise skip.SkipTest

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
