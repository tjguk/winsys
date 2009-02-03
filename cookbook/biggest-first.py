import threading
import time
import Queue

from winsys import fs

def file_sizes (start_from, results):
  for f in fs.flat (start_from):
    results.put (f)
  results.put (None)

def main ():
  start_from = "c:/temp"
  results = Queue.Queue ()
  threading.Thread (target=file_sizes, args=(start_from, results)).start ()
  
  sizes = []
  while True:
    f = results.get ()
    if f is None:
      break
    sizes.append (f)
    if len (sizes) % 20 == 0:
      print sorted (sizes, key=lambda f: f.size / time.mktime (f.created_at.timetuple ()))

if __name__ == '__main__':
  main ()
