import os, sys
import pythoncom
from win32com.shell import shell, shellcon

def tree (root=None, level=0):
  if level > 3: return
  if root is None:
    root = shell.SHGetDesktopFolder ()
    print root.GetDisplayNameOf ([], shellcon.SHGDN_NORMAL)

  for folder in root.EnumObjects (None, shellcon.SHCONTF_FOLDERS):
    print "  " * level, root.GetDisplayNameOf (folder, shellcon.SHGDN_NORMAL)
    try:
      tree (root.BindToObject (folder, None, shell.IID_IShellFolder), level+1)
    except pythoncom.com_error:
      pass

def walk (root=None):
  if root is None:
    root = shell.SHGetDesktopFolder ()
    name = root.GetDisplayNameOf ([], shellcon.SHGDN_NORMAL)

  folders = root.EnumObjects (None, shellcon.SHCONTF_FOLDERS)
  items = root.EnumObjects (None, shellcon.SHCONTF_NONFOLDERS)
  yield

def main ():
  tree ()

if __name__ == '__main__':
  main (*sys.argv[1:])
