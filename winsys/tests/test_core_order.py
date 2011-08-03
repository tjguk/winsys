import unittest as unittest0
try:
  unittest0.skipUnless
  unittest0.skip
except AttributeError:
  import unittest2 as unittest
else:
  unittest = unittest0
del unittest0

from winsys import core

class C (core._WinSysObject):

  def __init__ (self, x):
    self.x = x

  def __eq__ (self, other):
    return self.x == other.x

  def __lt__ (self, other):
    return self.x < other.x

  def __hash__ (self):
    return hash (self.x)

class TestCoreOrder (unittest.TestCase):

  def test_eq (self):
    assert C (1) == C (1)

  def test_ne (self):
    assert C (1) != C (2)

  def test_lt (self):
    assert C (1) < C (2)

  def test_le (self):
    assert C (1) <= C (2)
    assert C (1) <= C (1)

  def test_ge (self):
    assert C (2) >= C (1)
    assert C (2) >= C (2)

  def test_gt (self):
    assert C (2) > C (1)

  def test_hash (self):
    assert set ([C (0), C (1), C (1), C (2)]) == set ([C (0), C (1), C (2)])

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
