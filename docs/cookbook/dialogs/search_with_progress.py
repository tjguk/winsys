import os
from winsys import dialogs, fs

files_found = []
def searcher (root, pattern, text):
  for dir, dirs, files in fs.dir (root).walk (ignore_access_errors=True):
    yield dir.filepath
    for f in files:
      if f.like (pattern):
        try:
          if text in open (f.filepath).read ():
            files_found.append (f)
        except fs.exc.x_access_denied:
          pass
        
root, pattern, text = dialogs.progress_dialog (
  "Find text in files",
  searcher,
  ("Start from", os.getcwd ()),
  ("Files matching", "*.txt"),
  ("Text", "")
)

for f in files_found:
  print f
