import win32file
from winsys import constants

#
# Pull all file attributes known to win32file
#
FILE_ATTRIBUTE = constants.Constants.from_pattern (u"FILE_ATTRIBUTE_*", namespace=win32file)
FILE_ATTRIBUTE.dump ()

#
# Add extra file attributes added since win32file
#
extras = dict (
  SPARSE_FILE = 0x00000200,
  REPARSE_POINT = 0x00000400 
)
FILE_ATTRIBUTE.update (extras)
FILE_ATTRIBUTE.dump ()