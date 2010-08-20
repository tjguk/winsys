from distutils.core import setup, Extension

import winsys

packages = ['winsys', 'winsys.tests', 'winsys._security', 'winsys.extras']
ext_modules = [
  Extension ("winsys._change_journal", ["src/_change_journal.c"]),
]

if __name__ == '__main__':
  setup (
      name='WinSys-3.x',
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
