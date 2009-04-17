import os
from winsys import dialogs, fs

DEFAULT = "temp.csv"
filename, = dialogs.dialog (
  "Open a filename",
  ("Filename", DEFAULT, dialogs.get_filename)
)

if not fs.file (filename):
  raise RuntimeError ("%s does not exist" % filename)
else:
  os.startfile (filename)