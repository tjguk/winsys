import threading

from winsys import ipc

def logger ():
  with ipc.mailslot ("logger") as l:
    while True:
      word = l.get ()
      if word == "STOP":
        break
      else:
        print word

threading.Thread (target=logger).start ()

with ipc.mailslot (r"\\*\mailslot\logger") as logging_mailslot:
  for word in "the quick brown fox".split ():
    logging_mailslot.put (word)
  logging_mailslot.put ("STOP")