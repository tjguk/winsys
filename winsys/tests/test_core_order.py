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

def test_eq ():
  assert C (1) == C (1)

def test_ne ():
  assert C (1) != C (2)

def test_lt ():
  assert C (1) < C (2)

def test_le ():
  assert C (1) <= C (2)
  assert C (1) <= C (1)

def test_ge ():
  assert C (2) >= C (1)
  assert C (2) >= C (2)

def test_gt ():
  assert C (2) > C (1)

def test_hash ():
  assert set ([C (0), C (1), C (1), C (2)]) == set ([C (0), C (1), C (2)])

if __name__ == "__main__":
  import nose
  nose.runmodule (exit=False)
  if sys.stdout.isatty (): raw_input ("Press enter...")
