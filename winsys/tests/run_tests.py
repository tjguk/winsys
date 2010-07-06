import os, sys
import glob
import imp
import unittest

IGNORE_DIRECTORIES = {'.svn'}

def add_tests_from_directory (suite, directory):
  print ("Adding tests from ", directory)
  for filepath in glob.glob (os.path.join (directory, "test_*.py")):
    module_name = os.path.basename (filepath).split (".")[0]
    pymodule = imp.load_source (module_name, filepath)

    for item in dir (pymodule):
      obj = getattr (pymodule, item)
      if isinstance (obj, type) and issubclass (obj, unittest.TestCase):
        suite.addTest (unittest.TestLoader ().loadTestsFromTestCase (obj))

def main (test_directory="."):
  suite = unittest.TestSuite ()
  add_tests_from_directory (suite, test_directory)
  for dirpath, dirnames, filenames in os.walk (test_directory):
    for id in IGNORE_DIRECTORIES:
      dirnames.remove (id)
    for dirname in dirnames:
      add_tests_from_directory (suite, os.path.join (dirpath, dirname))

  unittest.TextTestRunner (verbosity=2).run (suite)

if __name__ == '__main__':
  main (*sys.argv[1:])
