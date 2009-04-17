from __future__ import with_statement
from winsys import registry, accounts

new_key = registry.copy (r"HKLM\Software\Python", r"HKCU\Software\WinsysPython")

with new_key.security ("D") as sec:
  sec.break_inheritance (copy_first=False)
  sec.dacl = [
    (accounts.me (), "F", "ALLOW"),
    ("Authenticated Users", "R", "ALLOW")
  ]

new_key.dump ()
