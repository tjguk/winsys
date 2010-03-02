from winsys import fs
import os, sys
import tempfile
import uuid
import win32file
import utils

from nose.tools import *

FILE_ATTRIBUTE_ENCRYPTED = 
filenames = ["%d" % i for i in range (5)]
def setup ():
  utils.mktemp ()
  for filename in filenames:
    with open (os.path.join (utils.TEST_ROOT, filename), "w"):
      pass  

def teardown ():
  utils.rmtemp ()

def test_unicode ():
  path = unicode (os.path.dirname (sys.executable)).rstrip (fs.sep) + fs.sep
  assert_equal (path, fs.Dir (path))
  
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

def test_compress_not_contents ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  
  fs.Dir (filepath).compress (apply_to_contents=False)

  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_COMPRESSED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_COMPRESSED)

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

def test_encrypt ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  
  fs.Dir (filepath).encrypt ()

  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)

  fs.Dir (filepath).unencrypt ()

  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)

def test_encrypt_not_contents ():
  filepath = utils.TEST_ROOT
  
  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  
  fs.Dir (filepath).encrypt (apply_to_contents=False)

  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_false (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)

def test_unencrypt_not_contents ():
  filepath = utils.TEST_ROOT
  
  fs.Dir (filepath).encrypt ()
  assert_true (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)

  fs.Dir (filepath).unencrypt (apply_to_contents=False)

  assert_false (utils.attributes (filepath) & win32file.FILE_ATTRIBUTE_ENCRYPTED)
  for filename in filenames:
    assert_true (utils.attributes (os.path.join (filepath, filename)) & win32file.FILE_ATTRIBUTE_ENCRYPTED)


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

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
