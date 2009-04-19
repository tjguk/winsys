import os, sys
from winsys import security, fs

def find_uninherited_ace (file, ace_to_find, container_or_object):
  for ace in file.security ("D").dacl:
    if ace == ace_to_find and getattr (ace, "%ss_inherit" % container_or_object, 0):
      if not ace.inherited:
        return file, ace
      else:
        return find_uninherited_ace (file.parent (), ace_to_find, "container")

python = fs.file (sys.executable)
for ace in python.security ("D").dacl:
  if not ace.inherited:
    print python, ace
  else:
    f, ace_found = find_uninherited_ace (python.parent (), ace, "container" if isinstance (python, fs.Dir) else "object")
    print f, ace_found
