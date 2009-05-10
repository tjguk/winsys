import os
import contextlib
import re

import win32file

from winsys._fs.core import (
  sep, seps,
  wrapped,
  FILE_ACCESS, FILE_SHARE, FILE_CREATION, FILE_ATTRIBUTE, FILE_FLAG,
  PyHANDLE
)
from winsys import utils

LEGAL_FILECHAR = r"[^\?\*\\\:\/]"
LEGAL_FILECHARS = LEGAL_FILECHAR + "+"
LEGAL_VOLCHAR = r"[^\?\*\\\/]"
LEGAL_VOLCHARS = LEGAL_VOLCHAR + "+"
UNC = sep * 4 + LEGAL_FILECHARS + sep * 2 + LEGAL_FILECHARS
HEXDIGIT = "[0-9a-f]"
DRIVE = r"[A-Za-z]:"
VOLUME_PREAMBLE = sep * 4 + r"\?" + sep * 2 
VOLUME = VOLUME_PREAMBLE + "Volume\{%s{8}-%s{4}-%s{4}-%s{4}-%s{12}\}" % (HEXDIGIT, HEXDIGIT, HEXDIGIT, HEXDIGIT, HEXDIGIT)
DRIVE_VOLUME = VOLUME_PREAMBLE + DRIVE
PREFIX = r"((?:%s|%s|%s|%s)\\?)" % (UNC, DRIVE, VOLUME, DRIVE_VOLUME)
PATHSEG = "(" + LEGAL_FILECHARS + ")" + sep * 2 + "?"
PATHSEGS = "(?:%s)*" % PATHSEG
FILEPATH = PREFIX + PATHSEGS

def get_parts (filepath):
  ur"""Helper function to regularise a file path and then
  to pick out its drive and path components.
  
  Attempt to match the first part of the string against
  known path leaders::
  
    <drive>:\
    \\?\<drive>:\
    \\?\Volume{xxxx-...}\
    \\server\share\
  
  If that fails, assume the path is relative. 
  
  ============================= ======================================
  Path                          Parts
  ============================= ======================================
  c:/                           ["c:\\", ""]
  c:/t                          ["c:\\", "t"]
  c:/t/                         ["c:\\", "t", ""]
  c:/t/test.txt                 ["c:\\", "t", "test.txt"]
  c:/t/s/test.txt               ["c:\\", "t", "s", "test.txt"]
  c:test.txt                    ["c:\\", "", "test.txt"]
  s/test.txt                    ["", "s", "test.txt"]
  \\\\server\\share             ["\\\\server\\share\\", ""]
  \\\\server\\share\\a.txt      ["\\\\server\\share\\", "a.txt"]
  \\\\server\\share\\t\\a.txt   ["\\\\server\\share\\", "t", "a.txt"]
  \\\\?\\c:\test.txt            ["\\\\?\\c:\\", "test.txt"]
  \\\\?\\Volume{xxxx-..}\\t.txt ["\\\\?\Volume{xxxx-..}\\", "t.txt"]
  ============================= ======================================
  
  The upshot is that the first item in the list returned is
  always the root (including trailing slash except for the special
  case of the format <drive>:<path> representing the current directory
  on <drive>) if the path is absolute, an empty string if it is relative. 
  All other items before the last one represent the directories along
  the way. The last item is the filename, empty if the whole
  path represents a directory.
  
  The original filepath can usually be reconstructed as::
  
    from winsys import fs
    filepath = "c:/temp/abc.txt"
    parts = fs.get_parts (filepath)
    assert parts[0] + "\\".join (parts[1:]) == filepath
    
  The exception is when a root (UNC or volume) is given without
  a trailing slash. This is added in.

  Note that if the path does not end with a slash, the directory
  name itself is considered the filename. This is by design.
  """
  filepath = filepath.replace ("/", sep)
  prefix_match = re.match (PREFIX, filepath)
  
  if prefix_match:
    prefix = prefix_match.group (1)
    rest = filepath[len (prefix):]
    #
    # Special-case the un-rooted drive letter
    # so that paths of the form <drive>:<path>
    # are still valid, indicating <path> in the
    # current directory on <drive>
    #
    if prefix.startswith ("\\") or not prefix.endswith (":"):
      prefix = prefix.rstrip (sep) + sep
    return [prefix] + rest.split (sep)
  else:
    return [""] + filepath.split (sep)

def normalised (filepath):
  ur"""Convert any path or path-like object into the
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
  ur"""Helper function to return a file handle either for querying
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
  ur"""Return the handle passed or on newly-created for
  the filepath, making sure to close it afterwards
  """
  if isinstance (handle_or_filepath, PyHANDLE):
    handle_supplied = True
    hFile = handle_or_filepath
  else:
    handle_supplied = False
    hFile = handle (handle_or_filepath, write)
    
  yield hFile

  if not handle_supplied:
    hFile.close ()

def relative_to (filepath1, filepath2):
  ur"""Return filepath2 relative to filepath1. Both names
  are normalised first::
  
    ================ ================ ================
    filepath1        filepath2        result
    ---------------- ---------------- ----------------
    c:/a/b.txt       c:/a             b.txt
    ---------------- ---------------- ----------------
    c:/a/b/c.txt     c:/a             b/c.txt
    ---------------- ---------------- ----------------
    c:/a/b/c.txt     c:/a/b           c.txt
    ================ ================ ================
  
  :param filepath1: a file or directory
  :param filepath2: a directory
  :returns: filepath2 relative to filepath1
  """
  #
  # filepath2 must always be a directory; filepath1 may
  # be a file or a directory.
  #
  return utils.relative_to (normalised (filepath1), normalised (filepath2.rstrip (seps) + sep))