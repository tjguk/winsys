from __future__ import with_statement
import uuid
from winsys import accounts, security, fs

username = filename = str (uuid.uuid1 ())[:8]
user = accounts.User.create (username, "password")
f = fs.file (filename)
assert (not f)

assert accounts.me () != user
try:
  with user:
    assert accounts.me () == user
    f.touch ()
    assert f.security ().owner == user
    f.delete ()
finally:
  user.delete ()
