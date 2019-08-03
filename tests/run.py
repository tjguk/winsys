# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys
import glob
import imp
from winsys._compat import unittest

IGNORE_DIRECTORIES = set(['.svn', "build", "dist"])

def add_tests_from_directory(suite, directory):
    skipped_modules = []
    for filepath in glob.glob(os.path.join(directory, "test_*.py")):
        module_name = os.path.basename(filepath).split(".")[0]
        print("Loading", module_name)
        pymodule = imp.load_source(module_name, filepath)
        for item in dir(pymodule):
            obj = getattr(pymodule, item)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                suite.addTest(unittest.TestLoader().loadTestsFromTestCase(obj))

def main(test_directory="."):
    sys.stdout.write("\n\nRunning for %s\n" % sys.version)
    suite = unittest.TestSuite()
    add_tests_from_directory(suite, test_directory)
    for dirpath, dirnames, filenames in os.walk(test_directory):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRECTORIES]
        for dirname in dirnames:
            add_tests_from_directory(suite, os.path.join(dirpath, dirname))

    result = unittest.TextTestRunner(verbosity=1, failfast=False).run(suite)
    if result.errors or result.failures:
        sys.exit(1)
    else:
        sys.exit(0)
