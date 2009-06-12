from __future__ import with_statement
from winsys import registry, accounts

new_key = registry.copy (r"HKLM\Software\Python", r"HKLM\Software\WinsysPython")

try:
  with new_key.security () as sec:
    sec.break_inheritance (copy_first=False)
    sec.dacl += [
      ("Users", "R", "ALLOW"),
      (accounts.me (), "F", "ALLOW"),
    ]
    sec.dump ()

finally:
  print "***"
  new_key.security ().dump ()
