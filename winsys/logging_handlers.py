import marshal
import logging

from winsys import constants, core, ipc
from winsys.exceptions import *

class MailslotHandler (logging.Handler):
  """A logging-compatible handler which will write to a named
  mailslot. The data is marshalled before being sent which means
  that only Python primitives may be sent, but allows, eg, None
  to be used as a sentinel value.
  """

  def __init__(self, mailslot_name):
    logging.Handler.__init__ (self)
    self.mailslot_name = mailslot_name
    
  def put (self, msg):
    ipc.mailslot (self.mailslot_name).put (marshal.dumps (msg))
  
  def emit (self, record):
    self.put (self.format (record))
    
  def close (self):
    try:
      self.put (None)
    except x_not_found:
      pass

class PermanentMailslotHandler (MailslotHandler):
  """Subclass the MailslotHandler but take no action on closedown.
  This is intended to be used when the receiving mailslot is running
  permanently so shouldn't be closed when the logging process finishes.
  """
  def close (self):
    return

if __name__ == '__main__':
  import sys
  import subprocess
  import logging
  import time
  import uuid
  mailslot_name = str (uuid.uuid1 ())
  subprocess.Popen ([sys.executable, "extras/mailslot_listener.pyw", mailslot_name])
  time.sleep (1)
  logger = logging.getLogger (mailslot_name)
  logger.setLevel (logging.DEBUG)
  logger.addHandler (MailslotHandler (mailslot_name))
  logger.debug ("DEBUG")
  logger.info ("INFO")
  logger.warn ("WARN")
  logger.error ("ERROR")
  raw_input ("Press enter...")