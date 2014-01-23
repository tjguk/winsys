# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from winsys._compat import unittest
from winsys import environment

#
# For now, do just enough to exercise the module:
# ensure that it imports and that basically functionality
# functions
#
class TestEnvironmentBasic(unittest.TestCase):
    """
    Do just enough to exercise the module:
    ensure that it imports and that basically functionality
    functions
    """

    def test_user_environment(self):
        self.assertTrue(environment.user())

    def test_system_environment(self):
        self.assertTrue(environment.system())

    def test_system_environment(self):
        self.assertTrue(environment.process())

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
