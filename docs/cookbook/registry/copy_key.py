from __future__ import with_statement
from winsys import registry, accounts

new_key = registry.copy (r"HKLM\Software\Python", r"HKLM\Software\WinsysPython")

with new_key.security ("D") as sec:
  sec.break_inheritance (copy_first=False)
  sec.dacl = [
    ("Users", "R", "ALLOW"),
    ("CREATOR OWNER", "F", "ALLOW"),
  ]
  sec.dump ()

#~ new_key.dump ()
