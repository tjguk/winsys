import sys
from winsys import fs, security

for dace in security.security (sys.executable).dacl:
  print dace.trustee, fs.FILE_ACCESS.names_from_value (dace.access)
