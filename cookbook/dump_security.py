import tempfile

from winsys import security

FILENAME = tempfile.mktemp ()
open (FILENAME, "w").close ()
security.Security.from_object (FILENAME).dump ()
input ("Press enter...")
