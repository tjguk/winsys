import os, sys
import tempfile
import unittest
import uuid

import win32file

from winsys.tests.test_fs import utils
from winsys import fs

class TestFS (unittest.TestCase):

  filenames = ["%d" % i for i in range (5)]

  def setup (self):
    utils.mktemp ()
    for filename in self.filenames:
      with open (os.path.join (utils.TEST_ROOT, filename), "w"):
        pass

  def teardown (self):
    utils.rmtemp ()

  def test_glob (self):
    import glob
    pattern = os.path.join (utils.TEST_ROOT, "*")
    self.assertEquals (list (fs.glob (pattern)), glob.glob (pattern))

  def test_listdir (self):
    import os
    self.assertEquals (list (fs.listdir (utils.TEST_ROOT)), os.listdir (utils.TEST_ROOT))

#
# All the other module-level functions are hand-offs
# to the corresponding Entry methods.
#

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
