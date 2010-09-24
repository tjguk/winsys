import os, sys
from distutils.core import setup, Extension
if sys.version_info >= (3,):
  import lib2to3.refactor
  fixers = lib2to3.refactor.get_fixers_from_package ("lib2to3.fixes")
  refactorer = lib2to3.refactor.RefactoringTool (fixers)
else:
  refactorer = None

import winsys

packages = ['winsys', 'winsys.tests', 'winsys._security', 'winsys.extras']
ext_modules = [
  Extension ("winsys._change_journal", ["src/_change_journal.c"]),
]

if __name__ == '__main__':
  if refactorer:
    refactorer.refactor_dir (".", write=True)
  setup (
      name='WinSys-%d.x' % (sys.version_info[0]),
      version='0.5.2',
      url='http://code.google.com/p/winsys',
      #~ download_url='http://timgolden.me.uk/python/downloads/winsys',
      license='LICENSE.txt',
      author='Tim Golden',
      author_email='mail@timgolden.me.uk',
      description='Python tools for the Windows sysadmin',
      long_description=open ("README.txt").read (),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: Microsoft :: Windows :: Windows NT/2000',
          'Programming Language :: Python :: 3',
          'Topic :: Utilities',
      ],
      platforms='win32',
      packages=packages,
      ext_modules=[] ## ext_modules
  )
