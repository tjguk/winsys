# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys

import win32api

from winsys._compat import unittest
from winsys import _advapi32

@unittest.skip("Enable this and fill in credentials if you want it to run")
class TestBasic(unittest.TestCase):
    """
    Do just enough to exercise the module: ensure that it imports
    and that basically functionality functions
    """
    def test_create_process_with_logonw(self):
        _advapi32.CreateProcessWithLogonW(
            username=None,
            domain=None,
            password=None,
            command_line='%s -c "import sys; print(sys.executable)"' % sys.executable
        )

if __name__ == "__main__":
  unittest.main()
  if sys.stdout.isatty(): raw_input("Press enter...")
