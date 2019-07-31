# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys

import win32file

from winsys._compat import unittest
from winsys._compat import *
from winsys.tests import utils as testutils
from winsys import _kernel32

class TestBasic(unittest.TestCase):
    """
    Do just enough to exercise the module: ensure that it imports
    and that basically functionality functions
    """

    @staticmethod
    def get_volume_for_c_drive():
        return win32file.GetVolumeNameForVolumeMountPoint("C:\\")

    def test_find_first_volume(self):
        self.assertIsInstance(_kernel32.FindFirstVolume(), tuple)

    def test_find_next_volume(self):
        handle, _ = _kernel32.FindFirstVolume()
        try:
            self.assertIsInstance(_kernel32.FindNextVolume(handle), unicode)
        finally:
            _kernel32.FindVolumeClose(handle)

    @unittest.skipUnless(testutils.i_am_admin(), "These tests must be run as Administrator")
    @unittest.skip("Not used at present")
    def test_find_first_volume_mount_point(self):
        self.assertIsInstance(_kernel32.FindFirstVolumeMountPoint(self.get_volume_for_c_drive()), tuple)

    @unittest.skipUnless(testutils.i_am_admin(), "These tests must be run as Administrator")
    @unittest.skip("Not used at present")
    def test_find_next_volume_mount_point(self):
        handle, _ = _kernel32.FindFirstVolumeMountPoint(self.get_volume_for_c_drive())
        try:
            self.assertIsInstance(_kernel32.FindNextVolumeMountPoint(handle), str)
        finally:
            _kernel32.FindVolumeMountPointClose(handle)

    def test_get_compressed_file_size(self):
        self.assertIsInstance(_kernel32.GetCompressedFileSize(sys.executable), (int, long))

if __name__ == "__main__":
  unittest.main()
  if sys.stdout.isatty(): raw_input("Press enter...")
