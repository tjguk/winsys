# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys

import win32api

from winsys._compat import unittest
from winsys._compat import *
from . import utils as testutils
from winsys import processes

@unittest.skip("Not yet working")
class TestBasic(unittest.TestCase):
    """
    Do just enough to exercise the module: ensure that it imports
    and that basically functionality functions
    """

    def test_process(self):
        p = processes.process()
        pid = win32api.GetCurrentProcessId()
        self.assertEqual(p.pid, pid)

if __name__ == "__main__":
  unittest.main()
  if sys.stdout.isatty(): raw_input("Press enter...")
