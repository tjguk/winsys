import os
import re

from .core import *

def get_parts (filepath):
  u"""Helper function to regularise a file path and then
  to pick out its drive and path components.
  
  Attempt to match the first part of the string against
  known path leaders:
  
  <drive>:\
  \\?\<drive>:\
  \\server\share\
  
  If that fails, assume it's relative to the current drive
  and/or directory.
  """
  filepath = filepath.replace ("/", "\\")
  prefix_match = re.match (ur"([A-Za-z]:\\)", filepath)
  if not prefix_match:
    prefix_match = re.match (ur"(\\\\\?\\[A-Za-z]:\\)", filepath)
    if not prefix_match:
      prefix_match = re.match (ur"(\\\\[^\?\*\\\:\/]+\\[^\?\*\\\:\/]+\\)", filepath)
  
  if prefix_match:
    prefix = prefix_match.group (1)
    rest = filepath[len (prefix):]
    return [prefix] + rest.split (sep)
  else:
    #
    # Assume it's relative to the current drive
    #
    if filepath.startswith (sep):
      prefix = get_parts (os.getcwd ())[0].rstrip (seps)
    else:
      prefix = os.getcwd ()
    filepath = os.path.join (prefix, filepath)
    return get_parts (filepath)
