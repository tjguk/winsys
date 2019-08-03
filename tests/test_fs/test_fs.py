# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys
import tempfile
from winsys._compat import unittest
import uuid

import win32file

from . import utils as fsutils
from winsys import fs

class TestFS (unittest.TestCase):

  filenames = ["%d" % i for i in range (5)]

  def setUp (self):
    fsutils.mktemp ()
    for filename in self.filenames:
      with open (os.path.join (fsutils.TEST_ROOT, filename), "w"):
        pass

  def tearDown (self):
    fsutils.rmtemp ()

  def test_glob (self):
    import glob
    pattern = os.path.join (fsutils.TEST_ROOT, "*")
    self.assertEqual (list (fs.glob (pattern)), glob.glob (pattern))

  def test_listdir (self):
    import os
    fs_version = list (fs.listdir (fsutils.TEST_ROOT))
    os_version = os.listdir (fsutils.TEST_ROOT)
    self.assertEqual (fs_version, os_version, "%s differs from %s" % (fs_version, os_version))

#
# All the other module-level functions are hand-offs
# to the corresponding Entry methods.
#

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
