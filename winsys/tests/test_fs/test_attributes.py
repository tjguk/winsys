import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0

from winsys import fs, constants

CONST = constants.Constants.from_dict (dict (
  a = 1,
  b = 2,
  c = 4
))

class TestAttributes (unittest.TestCase):

  def test_getitem_text (self):
    attributes = constants.Attributes (3, CONST)
    self.assertTrue (attributes["a"])
    self.assertFalse (attributes["c"])

  def test_getitem_number (self):
    attributes = constants.Attributes (3, CONST)
    self.assertTrue (attributes[1])
    self.assertFalse (attributes[4])

  def test_getattr (self):
    attributes = constants.Attributes (3, CONST)
    self.assertTrue (attributes.a)
    self.assertFalse (attributes.c)

  def test_contains (self):
    attributes = constants.Attributes (3, CONST)
    self.assertTrue ("a" in attributes)
    self.assertFalse ("c" in attributes)

  def test_string (self):
    attributes = constants.Attributes (3, CONST)
    self.assertEquals (attributes.as_string (), "%08X" % 3)

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
