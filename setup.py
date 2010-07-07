from distutils.core import setup, Extension

import winsys

packages = ['winsys', 'winsys.tests', 'winsys._security', 'winsys.extras']
ext_modules = [
  Extension ("winsys._change_journal", ["src/_change_journal.c"]),
]

if __name__ == '__main__':
  setup (
      name='WinSys',
      version=winsys.__version__,
      url='http://code.google.com/p/winsys',
      download_url='http://timgolden.me.uk/python/downloads/winsys',
      license='MIT',
      author='Tim Golden',
      author_email='mail@timgolden.me.uk',
      description='Python tools for the Windows sysadmin',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: Windows',
          'Programming Language :: Python',
          'Topic :: Utilities',
      ],
      platforms='win32',
      packages=packages,
      ext_modules=ext_modules
  )
