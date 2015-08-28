#!python3
import os, sys
print(sys.executable)
from winsys import fs, dialogs
print(dialogs.dialog("abc", ("def", ["1", "2", "3"])))
