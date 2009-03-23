import os
import contextlib
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

def handle (filepath, write=False):
  u"""Helper function to return a file handle either for querying
  (the default case) or for writing -- including writing directories
  """
  return wrapped (
    win32file.CreateFile,
    normalised (filepath),
    (FILE_ACCESS.READ | FILE_ACCESS.WRITE) if write else 0,
    (FILE_SHARE.READ | FILE_SHARE.WRITE) if write else FILE_SHARE.READ,
    None,
    FILE_CREATION.OPEN_EXISTING,
    FILE_ATTRIBUTE.NORMAL | FILE_FLAG.BACKUP_SEMANTICS,
    None
  )

@contextlib.contextmanager
def Handle (handle_or_filepath, write=False):
  u"""Return the handle passed or on newly-created for
  the filepath, making sure to close it afterwards
  """
  if isinstance (handle_or_filepath, PyHANDLE):
    handle_supplied = True
    hFile = handle_or_filepath
  else:
    handle_supplied = False
    hFile = handle (handle_or_filepath)
    
  yield hFile

  if not handle_supplied:
    hFile.close ()

