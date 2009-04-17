from __future__ import with_statement
import uuid
from winsys import accounts, security

username = str (uuid.uuid1 ())[:8]
user = accounts.User.create (username, "password")
try:
  with user:
    open ("temp.txt", "w").close ()

  assert security.security ("temp.txt").owner == user
finally:
  user.delete ()
