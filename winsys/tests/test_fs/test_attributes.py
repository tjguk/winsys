from winsys import fs, constants

from nose.tools import *

CONST = constants.Constants.from_dict (dict (
  a = 1,
  b = 2,
  c = 4
))

def test_getitem_text ():
  attributes = fs._Attributes (3, CONST)
  assert_true (attributes["a"])
  assert_false (attributes["c"])

def test_getitem_number ():
  attributes = fs._Attributes (3, CONST)
  assert_true (attributes[1])
  assert_false (attributes[4])

def test_getattr ():
  attributes = fs._Attributes (3, CONST)
  assert_true (attributes.a)
  assert_false (attributes.c)

def test_contains ():
  attributes = fs._Attributes (3, CONST)
  assert_true ("a" in attributes)
  assert_false ("c" in attributes)

def test_string ():
  attributes = fs._Attributes (3, CONST)
  assert_equals (attributes.as_string (), "%08X" % 3)

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
