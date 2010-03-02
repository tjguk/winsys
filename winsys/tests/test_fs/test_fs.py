from winsys import fs
import os, sys
import tempfile
import uuid
import win32file
import utils

from nose.tools import *

filenames = ["%d" % i for i in range (5)]
def setup ():
  utils.mktemp ()
  for filename in filenames:
    with open (os.path.join (utils.TEST_ROOT, filename), "w"):
      pass  

def teardown ():
  utils.rmtemp ()

def test_glob ():
  import glob
  pattern = os.path.join (utils.TEST_ROOT, "*")
  assert_equal (list (fs.glob (pattern)), glob.glob (pattern))

def test_listdir ():
  import os
  assert_equal (list (fs.listdir (utils.TEST_ROOT)), os.listdir (utils.TEST_ROOT))

#
# All the other module-level functions are hand-offs
# to the corresponding Entry methods.
#

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
