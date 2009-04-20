from winsys import fs, security

full_control = security.ace ((security.me (), "F", "ALLOW"))

def take_control (f):
  f.take_ownership ()
  with f.security () as s:
    s.dacl.append (full_control)

start_from = fs.dir (raw_input ("Start from: "))
take_control (start_from)
for f in start_from.flat (includedirs=True):
  print f
  take_control (f)
