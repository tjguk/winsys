import os, sys
import glob
import imp
import unittest

def main (test_directory="."):
  suite = unittest.TestSuite ()

  for filepath in glob.glob (os.path.join (test_directory, "test_*.py")):
    module_name = os.path.basename (filepath).split (".")[0]
    pymodule = imp.load_source (module_name, filepath)

    for item in dir (pymodule):
      obj = getattr (pymodule, item)
      if isinstance (obj, type) and issubclass (obj, unittest.TestCase):
        suite.addTest (unittest.TestLoader ().loadTestsFromTestCase (obj))

  unittest.TextTestRunner (verbosity=2).run (suite)

if __name__ == '__main__':
  main (*sys.argv[1:])
