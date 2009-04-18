import operator
from winsys import dialogs, fs, utils

[root] = dialogs.dialog (
  "Find top-level sizes",
  ("Start from", "", dialogs.get_folder)
)

sizes = dict (
  (d, sum (f.size for f in d.flat ())) 
    for d in fs.dir (root).dirs ()
)
for d, size in sorted (sizes.items (), key=operator.itemgetter (1), reverse=True):
  print d.name, "=>", utils.size_as_mb (size)
