# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys

from winsys._compat import unittest
from winsys._compat import *
from winsys.tests import utils as testutils
from winsys import constants

class A(object):
    zero = 0
    x = 1
    y = 2
    z = 4
    f_a = 8
    f_b = 16
    f_c = 32

class TestBasic(unittest.TestCase):
    """
    Do just enough to exercise the module: ensure that it imports
    and that basically functionality functions
    """

    def test_from_pattern_no_pattern(self):
        self.assertEqual(constants.from_pattern(None, "abc"), "abc")

    def test_from_pattern(self):
        self.assertEqual(constants.from_pattern("TEST_*", "TEST_abc"), "abc")

    def test_constants_from_list(self):
        c = constants.Constants.from_list(['x', 'y', 'z'], namespace=A)
        self.assertEqual(c.x, A.x)
        self.assertEqual(c['x'], A.x)

    def test_constants_from_pattern(self):
        c = constants.Constants.from_pattern("f_*", namespace=A)
        self.assertEqual(c.a, A.f_a)
        self.assertEqual(c['b'], A.f_b)
        self.assertEqual(c.c, A.f_c)

    def test_constants_from_pattern_with_exclusion(self):
        c = constants.Constants.from_pattern("f_*", excluded=["f_b"], namespace=A)
        self.assertEqual(c.a, A.f_a)
        self.assertEqual(c['c'], A.f_c)
        self.assertRaises(AttributeError, getattr, c, "b")

    def test_name_from_value(self):
        c = constants.Constants.from_pattern(namespace=A)
        self.assertEqual(c.name_from_value(0), "zero")
        self.assertEqual(c.name_from_value(32), "f_c")

    def test_names_from_value_nonzero(self):
        c = constants.Constants.from_pattern(namespace=A)
        self.assertEqual(c.names_from_value(4), ["z"])

    def test_names_from_value_zero(self):
        c = constants.Constants.from_pattern(namespace=A)
        self.assertEqual(c.names_from_value(0), ["zero"])

if __name__ == "__main__":
  unittest.main()
  if sys.stdout.isatty(): raw_input("Press enter...")
