import tempfile

from winsys import security

FILENAME = tempfile.mktemp ()
open (FILENAME, "w").close ()
security.Security.read (FILENAME).dump ()
raw_input ("Press enter...")
