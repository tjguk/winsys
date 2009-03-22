import re

from .core import *

def get_parts (filepath):
  u"""Helper function to regularise a file path and then
  to pick out its drive and path components.
  """
  filepath = filepath.replace ("/", "\\")
  prefix_match = re.match (ur"([A-Za-z]:\\)", filepath)
  if not prefix_match:
    prefix_match = re.match (ur"(\\\\\?\\[A-Za-z]:\\)", filepath)
    if not prefix_match:
      prefix_match = re.match (ur"(\\\\[^\?\*\\\:\/]+\\[^\?\*\\\:\/]+\\)", filepath)
      if not prefix_match:
        raise x_fs (u"Unable to match %s against known path types" % filepath)

  prefix = prefix_match.group (1)
  rest = filepath[len (prefix):]
  return [prefix] + rest.split (sep)
