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
      prefix_match = re.match (ur"(\\\\[^\?\*\\\:\/]+\\[^\?\*\\\:\/]+\\?)", filepath)
  
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

def normalised (filepath):
  u"""Convert any path or path-like object into the
  length-unlimited unicode equivalent. This should avoid
  issues with maximum path length and the like.
  """
  
  #
  # os.path.abspath will return a sep-terminated string
  # for the root directory and a non-sep-terminated
  # string for all other paths.
  #
  filepath = unicode (filepath)
  if filepath.startswith (2 * sep):
    return filepath
  else:
    is_dir = filepath[-1] in seps
    abspath = os.path.abspath (filepath)
    return (u"\\\\?\\" + abspath) + (sep if is_dir and not abspath.endswith (sep) else "")
