import random

from winsys import ipc

reader = ipc.mailslot ("reader")
writer = ipc.mailslot ("reader")

message = list (reversed ("the quick brown fox jumps over the lazy dog".split ()))

while True:
  try:
    data = reader.get (block=False, timeout_ms=1000)
    if data == "STOP":
      break
  except ipc.x_mailslot_empty:
    pass
  else:
    print data

  if random.randint (1, 100) > 95:
    try:
      writer.put (message.pop ())
    except IndexError:
      writer.put ("STOP")
