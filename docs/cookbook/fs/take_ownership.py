from __future__ import with_statement
from winsys import security, fs

f = fs.file ("c:/temp/tim.txt")
with security.change_privileges ([security.PRIVILEGE.TAKE_OWNERSHIP]):
  f.take_ownership ()

assert f.security ("O").owner == security.me ()
