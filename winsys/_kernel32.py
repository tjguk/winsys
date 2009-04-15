# -*- coding: iso-8859-1 -*-
u"""Provide functions unavailable via pywin32 which reside in kernel32.dll
"""
import winerror
from ctypes import windll, wintypes
import ctypes
import win32api
import win32file

from winsys import exc

kernel32 = windll.kernel32

class x_kernel32 (exc.x_winsys):
  pass

def error (exception, context="", message=""):
  errno = win32api.GetLastError ()
  message = message or win32api.FormatMessageW (errno)
  raise exception (errno, context, message)

VOLUME_NAME_LENGTH = 255

u"""The Find[First|Next]Volume and FindVolumeClose set provide
for a list of volumes which the system recognises. They are
wrapped as an iterator by functions in the fs module.
"""
def FindFirstVolume ():
  u"""Find the first volume which the system recognises. If
  none is found, raise x_kernel32. Otherwise return the
  search handle and the volume name.
  """
  volume_name = ctypes.create_unicode_buffer (u" " * VOLUME_NAME_LENGTH)
  hSearch = kernel32.FindFirstVolumeW (volume_name, VOLUME_NAME_LENGTH)
  if hSearch == win32file.INVALID_HANDLE_VALUE:
    return error (x_kernel32, "FindFirstVolume")
  else:
    return hSearch, volume_name.value

def FindNextVolume (hSearch):
  u"""Find the next volume which the system recognises in
  the set provided by a search handle returned by FindFirstVolume.
  If there are no more in this set, close the handle and return
  None.
  """
  volume_name = ctypes.create_unicode_buffer (u" " * VOLUME_NAME_LENGTH)
  if kernel32.FindNextVolumeW (hSearch, volume_name, VOLUME_NAME_LENGTH) != 0:
    return volume_name.value
  else:
    errno = ctypes.GetLastError ()
    if errno == winerror.ERROR_NO_MORE_FILES:
      FindVolumeClose (hSearch)
      return None
    else:
      return error (x_kernel32, "FindNextVolume")

def FindVolumeClose (hSearch):
  u"""Close a search handle opened by FindFirstVolume, typically
  after the last volume has been returned.
  """
  if kernel32.FindVolumeClose (hSearch) == 0:
      return error (x_kernel32, "FindVolumeClose")

u"""The Find[First|Next]VolumeMountPoint and FindVolumeMountPointClose 
set provide for a list of volume mount points which the system recognises. 
They are wrapped as an iterator by functions in the fs module.
"""
def FindFirstVolumeMountPoint (volume_name):
  u"""Find the first volume mount point which the system recognises. 
  If none is found, raise x_kernel32. Otherwise return the
  search handle and the volume mount point name.
  """
  volume_mount_point_name = ctypes.create_unicode_buffer (u" " * VOLUME_NAME_LENGTH)
  hSearch = kernel32.FindFirstVolumeMountPointW (volume_name, volume_mount_point_name, VOLUME_NAME_LENGTH)
  if hSearch == win32file.INVALID_HANDLE_VALUE:
    return error (x_kernel32, "FindFirstVolumeMountPoint")
  else:
    return hSearch, volume_mount_point_name.value
  
def FindNextVolumeMountPoint (hSearch):
  u"""Find the next volume mount point which the system recognises in
  the set provided by a search handle returned by FindFirstVolumeMountPoint.
  If there are no more in this set, close the handle and return None.
  """
  volume_mount_point_name = ctypes.create_unicode_buffer (u" " * VOLUME_NAME_LENGTH)
  if kernel32.FindNextVolumeMountPointW (hSearch, volume_mount_point_name, VOLUME_NAME_LENGTH) != 0:
    return volume_mount_point_name.value
  else:
    if ctypes.GetLastError () == winerror.ERROR_NO_MORE_FILES:
      FindVolumeMountPointClose (hSearch)
      return None
    else:
      return error (x_kernel32, "FindNextVolumeMountPoint")

def FindVolumeMountPointClose (hSearch):
  u"""Close a search handle opened by FindFirstVolumeMountPoint, typically
  after the last volume mount point has been returned.
  """
  if kernel32.FindVolumeMountPointClose (hSearch) == 0:
    return error (x_kernel32, "FindVolumeMountPointClose")

def GetCompressedFileSize (filepath):
  u"""Return the size in bytes of a file. If the file is compressed,
  return the compressed size, otherwise return the regular size.
  
  Altho' this function is already exposed by pywin32, there is a
  bug in the implementation such that non-trivial unicode causes
  an error.
  """
  hi = wintypes.DWORD ()
  lo = kernel32.GetCompressedFileSizeW (unicode (filepath), ctypes.byref (hi))
  if lo == 0xffffffff and ctypes.GetLastError != winerror.NO_ERROR:
    return error (x_kernel32, "GetCompressedFileSize")
  else:
    return lo + (hi.value * 2 << 31)
