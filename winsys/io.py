# -*- coding: iso-8859-1 -*-
import pywintypes
import winerror
import win32con
import win32event
import win32file
import ntsecuritycon

from winsys import constants, core, exc, utils

PyHANDLE = pywintypes.HANDLEType

FILE_ACCESS = constants.Constants.from_pattern ("FILE_*", namespace=ntsecuritycon)
FILE_ACCESS.update (constants.STANDARD_ACCESS)
FILE_ACCESS.update (constants.GENERIC_ACCESS)
FILE_ACCESS.update (constants.ACCESS)
FILE_ACCESS.doc ("File-specific access rights")

FILE_SHARE = constants.Constants.from_pattern (u"FILE_SHARE_*", namespace=win32file)
FILE_SHARE.doc (u"Ways of sharing a file for reading, writing, &c.")

FILE_CREATION = constants.Constants.from_list ([
  u"CREATE_ALWAYS",
  u"CREATE_NEW",
  u"OPEN_ALWAYS",
  u"OPEN_EXISTING",
  u"TRUNCATE_EXISTING"
], namespace=win32con)
FILE_CREATION.doc (u"Options when creating a file")

class x_io (exc.x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_io)

def open (path, mode="r"):
  ur"""Return a file handle either for querying
  (the default case) or for writing -- including writing directories

  :param filepath: anything whose unicode representation is a valid file path
  :param write: is the handle to be used for writing [True]
  :param attributes: anything accepted by :const:`FILE_ATTRIBUTE`
  :return: an open file handle for reading or writing, including directories
  """
  attributes = FILE_ATTRIBUTE.constant (attributes)
  if attributes is None:
    attributes = FILE_ATTRIBUTE.NORMAL | FILE_FLAG.BACKUP_SEMANTICS
  if async:
    attributes |= FILE_FLAG.OVERLAPPED
  return wrapped (
    win32file.CreateFile,
    normalised (filepath),
    (io.FILE_ACCESS.READ | io.FILE_ACCESS.WRITE) if write else io.FILE_ACCESS.READ,
    (io.FILE_SHARE.READ | io.FILE_SHARE.WRITE) if write else io.FILE_SHARE.READ,
    sec,
    io.FILE_CREATION.OPEN_ALWAYS if write else io.FILE_CREATION.OPEN_EXISTING,
    attributes,
    None
  )

