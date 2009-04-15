import os

import ntsecuritycon
import pywintypes
import winerror
import win32con
import win32event
import win32file
import winioctlcon

from winsys import exc, constants

sep = unicode (os.sep)
seps = u"/\\"

class x_fs (exc.x_winsys):
  pass

class x_no_such_file (x_fs):
  pass

class x_too_many_files (x_fs):
  pass
  
class x_invalid_name (x_fs):
  pass
  
class x_no_certificate (x_fs):
  pass
  
class x_not_ready (x_fs):
  pass
  
WINERROR_MAP = {
  winerror.ERROR_ACCESS_DENIED : exc.x_access_denied,
  winerror.ERROR_PATH_NOT_FOUND : x_no_such_file,
  winerror.ERROR_FILE_NOT_FOUND : x_no_such_file,
  winerror.ERROR_BAD_NETPATH : x_no_such_file,
  winerror.ERROR_INVALID_NAME : x_invalid_name,
  winerror.ERROR_BAD_RECOVERY_POLICY : x_no_certificate,
  winerror.ERROR_NOT_READY : x_not_ready,
  winerror.ERROR_INVALID_HANDLE : exc.x_invalid_handle
}
wrapped = exc.wrapper (WINERROR_MAP, x_fs)

FILE_ACCESS = constants.Constants.from_pattern ("FILE_*", namespace=ntsecuritycon)
FILE_ACCESS.update (constants.STANDARD_ACCESS)
FILE_ACCESS.update (constants.GENERIC_ACCESS)
FILE_ACCESS.update (constants.ACCESS)
FILE_SHARE = constants.Constants.from_pattern (u"FILE_SHARE_*", namespace=win32file)
FILE_NOTIFY_CHANGE = constants.Constants.from_pattern (u"FILE_NOTIFY_CHANGE_*", namespace=win32con)
FILE_ACTION = constants.Constants.from_dict (dict (
  ADDED = 1,
  REMOVED = 2,
  MODIFIED = 3,
  RENAMED_OLD_NAME = 4,
  RENAMED_NEW_NAME = 5
))
FILE_ATTRIBUTE = constants.Constants.from_pattern (u"FILE_ATTRIBUTE_*", namespace=win32file)
FILE_ATTRIBUTE.update (dict (
  ENCRYPTED=0x00004000, 
  REPARSE_POINT=0x00000400,
  SPARSE_FILE=0x00000200,
  VIRTUAL=0x00010000,
  NOT_CONTENT_INDEXES=0x00002000,
))
PROGRESS = constants.Constants.from_pattern (u"PROGRESS_*", namespace=win32file)
MOVEFILE = constants.Constants.from_pattern (u"MOVEFILE_*", namespace=win32file)
FILE_FLAG = constants.Constants.from_pattern (u"FILE_FLAG_*", namespace=win32con)
FILE_CREATION = constants.Constants.from_list ([
  u"CREATE_ALWAYS", 
  u"CREATE_NEW", 
  u"OPEN_ALWAYS", 
  u"OPEN_EXISTING", 
  u"TRUNCATE_EXISTING"
], namespace=win32con)
VOLUME_FLAG = constants.Constants.from_dict (dict (
  FILE_CASE_SENSITIVE_SEARCH      = 0x00000001,
  FILE_CASE_PRESERVED_NAMES       = 0x00000002,
  FILE_UNICODE_ON_DISK            = 0x00000004,
  FILE_PERSISTENT_ACLS            = 0x00000008,
  FILE_FILE_COMPRESSION           = 0x00000010,
  FILE_VOLUME_QUOTAS              = 0x00000020,
  FILE_SUPPORTS_SPARSE_FILES      = 0x00000040,
  FILE_SUPPORTS_REPARSE_POINTS    = 0x00000080,
  FILE_SUPPORTS_REMOTE_STORAGE    = 0x00000100,
  FILE_VOLUME_IS_COMPRESSED       = 0x00008000,
  FILE_SUPPORTS_OBJECT_IDS        = 0x00010000,
  FILE_SUPPORTS_ENCRYPTION        = 0x00020000,
  FILE_NAMED_STREAMS              = 0x00040000,
  FILE_READ_ONLY_VOLUME           = 0x00080000,
  FILE_SEQUENTIAL_WRITE_ONCE      = 0x00100000,
  FILE_SUPPORTS_TRANSACTIONS      = 0x00200000  
), pattern=u"FILE_*")
DRIVE_TYPE = constants.Constants.from_pattern (u"DRIVE_*", namespace=win32file)
COMPRESSION_FORMAT = constants.Constants.from_dict (dict (
  NONE = 0x0000,   
  DEFAULT = 0x0001,   
  LZNT1 = 0x0002
))
FSCTL = constants.Constants.from_pattern (u"FSCTL_*", namespace=winioctlcon)

PyHANDLE = pywintypes.HANDLEType

