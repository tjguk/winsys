from __future__ import with_statement
from winsys import accounts, security

python = accounts.account ("python")
with python:
  open ("temp.txt", "w").close ()

assert security.security ("temp.txt").owner == python
