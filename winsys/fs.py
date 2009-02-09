# -*- coding: iso-8859-1 -*-
"""Provide a wrapper around common filesystem operations, including
iterating over the files in a directory structure and copying, 
moving and linking them. Wherever possible iterators are used,
making it possible to act on large directory structures without
loading them all into memory.
"""
from __future__ import with_statement
import os, sys
import collections
import contextlib
import datetime
import filecmp
import fnmatch
import operator
import re
import struct
import threading
import time

import ntsecuritycon
import pywintypes
import winerror
import win32api
import win32con
import win32event
import win32file

from winsys import constants, core, exceptions, security, utils, _kernel32

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

PyHANDLE = pywintypes.HANDLEType

sep = unicode (os.sep)
seps = u"/\\"

class x_fs (exceptions.x_winsys):
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
  None : x_fs,
  winerror.ERROR_ACCESS_DENIED : exceptions.x_access_denied,
  winerror.ERROR_PATH_NOT_FOUND : x_no_such_file,
  winerror.ERROR_FILE_NOT_FOUND : x_no_such_file,
  winerror.ERROR_BAD_NETPATH : x_no_such_file,
  winerror.ERROR_INVALID_NAME : x_invalid_name,
  winerror.ERROR_BAD_RECOVERY_POLICY : x_no_certificate,
  winerror.ERROR_NOT_READY : x_not_ready,
  winerror.ERROR_INVALID_HANDLE : exceptions.x_invalid_handle
}
wrapped = exceptions.wrapper (WINERROR_MAP)

def _get_parts (filepath):
  u"""Helper function to regularise a file path and then
  to pick out its drive and path components.
  """
  filepath = os.path.abspath (filepath)
  prefix_match = re.match (ur"([A-Za-z]:)", filepath)
  if not prefix_match:
    prefix_match = re.match (ur"(\\\\\?\\[A-Za-z]:)", filepath)
    if not prefix_match:
      prefix_match = re.match (ur"(\\\\[^\?\*\\\:\/]+\\[^\?\*\\\:\/]+)", filepath)
      if not prefix_match:
        raise x_fs (u"Unable to match %s against known path types" % filepath)
  
  prefix = prefix_match.group (1)
  return [prefix, sep] + filepath[1+len (prefix):].split (sep)

def handle (filepath, write=False):
  u"""Helper function to return a file handle either for querying
  (the default case) or for writing -- including writing directories
  """
  return wrapped (
    win32file.CreateFile,
    utils.normalised (filepath),
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

class Attributes (core._WinSysObject):
  u"""Simple class wrapper for the list of file attributes
  (readonly, hidden, &c.). 
  """
  
  def __init__ (self, flags=0):
    self.flags = flags
      
  def __getattr__ (self, attr):
    return bool (self.flags & FILE_ATTRIBUTE[attr.upper ()])
    
  def __contains__ (self, attr):
    return getattr (self, attr)
  
  def as_string (self):
    return "%08x" % self.flags
  
  def dumped (self, level=0):
    return utils.dumped (
      u"\n".join (u"%s => %s" % (k, bool (self.flags & v)) for k, v in sorted (FILE_ATTRIBUTE.items ())),
      level
    )

class FilePath (unicode):
  u"""Helper class which subclasses unicode, and can therefore be passed
  directly to API calls. It provides common operations on file paths:
  directory name, filename, parent directory &c.
  """
  def __new__ (meta, filepath, *args, **kwargs):
    filepath = os.path.abspath (filepath)
    return unicode.__new__ (meta, filepath, *args, **kwargs)

  def __init__ (self, filepath, *args, **kwargs):
    u"""Break the filepath into its component parts, adding useful
    ones as instance attributes:
    
    FilePath.parts - a list of the components
    FilePath.root - always a backslash
    FilePath.filename - final component (may be blank)
    FilePath.name - same as filename unless empty in which case second-last component
    FilePath.dirname - all path components before the last
    FilePath.path - combination of volume and dirname
    FilePath.parent - combination of volume and all path components before second penultimate
    """
    self._parts = None
    self._root = None
    self._filename = None
    self._name = None
    self._dirname= None
    self._path = None
    self._parent = None
      
  def dump (self, level=0):
    print self.dumped (level=level)
  
  def dumped (self, level=0):
    output = []
    output.append (self)
    output.append (u"parts: %s" % self.parts)
    output.append (u"root: %s" % self.root)
    output.append (u"dirname: %s" % self.dirname)
    output.append (u"path: %s" % self.path)
    output.append (u"filename: %s" % self.filename)
    if self.parent:
      output.append (u"parent: %s" % self.parent)
    return utils.dumped (u"\n".join (output), level)
  
  def _get_parts (self):
    if self._parts is None:
      normself = utils.normalised (self)
      root = wrapped (win32file.GetVolumePathName, normself)
      rest = normself[len (root):]
      self._parts = [root] + rest.split (sep)
    return self._parts
  parts = property (_get_parts)
  
  def _get_root (self):
    if self._root is None:
      self._root = self.parts[0]
    return self._root
  root = property (_get_root)
  
  def _get_filename (self):
    if self._filename is None:
      self._filename = self.parts[-1]
    return self._filename
  filename = property (_get_filename)
  
  def _get_dirname (self):
    if self._dirname is None:
      self._dirname = sep + sep.join (self.parts[1:-1])
    return self._dirname
  dirname = property (_get_dirname)
  
  def _get_path (self):
    if self._path is None:
      self._path = self.root + self.dirname
    return self._path
  path = property (_get_path)
  
  def _get_parent (self):
    if self._parent is None:
      parent_dir = [p for p in self.parts if p][:-1]
      if parent_dir:
        self._parent = parent_dir[0] + sep.join (parent_dir[1:])
      else:
        self._parent = None
    return self._parent
  parent = property (_get_parent)
  
  def _get_name (self):
    if self._name is None:
      self._name = self.parts[-1] or self.parts[-2]
    return self._name
  name = property (_get_name)
  
  def __getitem__ (self, index):
    return self.parts[index]
  
  def __add__ (self, other):
    return self.__class__ (os.path.join (unicode (self), unicode (other)))
  
  def relative_to (self, other):
    return utils.relative_to (self, unicode (other))

class Drive (core._WinSysObject):
  
  def __init__ (self, drive):
    self.name = drive.rstrip (sep) + sep
    self.type = wrapped (win32file.GetDriveTypeW, self.name)
    
  def as_string (self):
    return "Drive %s" % self.name
  
  def _get_volume (self):
    try:
      return volume (self.name)
    except x_no_such_file:
      return None
  volume = property (_get_volume)
  
  def mount (self, vol):
    mount (self.name, vol)
  
  def dismount (self):
    dismount (self.name)
  
  def dumped (self, level):
    output = []
    output.append (u"name: %s" % self.name)
    output.append (u"type: %s" % DRIVE_TYPE.name_from_value (self.type))
    if self.volume:
      output.append (u"volume:\n%s" % self.volume.dumped (level))
    mount_points = [(mount_point, volume) for (mount_point, volume) in mounts () if mount_point.filepath.startswith (self.name)]
    output.append (u"mount_points:\n%s" % utils.dumped_list ((u"%s => %s" % i for i in mount_points), level))
    return utils.dumped ("\n".join (output), level)

def drives ():
  for drive in wrapped (win32api.GetLogicalDriveStrings).strip ("\x00").split ("\x00"):
    yield Drive (drive)

class Volume (core._WinSysObject):
  
  def __init__ (self, volume):
    self.name = volume
    
  def as_string (self):
    return self.name
    
  def _get_info (self):
    try:
      return wrapped (win32api.GetVolumeInformation, self.name)
    except x_not_ready:
      return [None, None, None, 0, None]
    
  def _get_label (self):
    return self._get_info ()[0]
  label = property (_get_label)
  
  def _get_serial_number (self):
    value = self._get_info ()[1]
    if value is None:
      return None
    else:
      serial_number, = struct.unpack ("L", struct.pack ("l", value))
      return serial_number
  serial_number = property (_get_serial_number)
  
  def _get_maximum_component_length (self):
    return self._get_info ()[2]
  maximum_component_length = property (_get_maximum_component_length)
  
  def _get_flags (self):
    return self._get_info ()[3]
  flags = property (_get_flags)
  
  def _get_file_system_name (self):
    return self._get_info ()[4]
  file_system_name = property (_get_file_system_name)
  
  def _get_mounts (self):
    return wrapped (win32file.GetVolumePathNamesForVolumeName, self.name)
  mounts = property (_get_mounts)
    
  def dumped (self, level):
    output = []
    output.append (u"volume: %s" % self.name)
    output.append (u"mounted at:\n%s" % utils.dumped_list (self.mounts, level))
    output.append (u"label: %s" % self.label)
    if self.serial_number is not None:
      output.append (u"serial_number: %08x" % self.serial_number)
    output.append (u"maximum_component_length: %s" % self.maximum_component_length)
    output.append (u"flags:\n%s" % utils.dumped_flags (self.flags, VOLUME_FLAG, level))
    output.append (u"file_system_name: %s" % self.file_system_name)
    return utils.dumped (u"\n".join (output), level)
    
  def mount (self, filepath):
    mount (filepath, self)
    
  def dismount (self, filepath):
    dismount (filepath)
        
def volume (volume):
  if isinstance (volume, Volume):
    return volume
  elif volume.startswith (ur"\\?\Volume"):
    return Volume (volume)
  else:
    return Volume (wrapped (win32file.GetVolumeNameForVolumeMountPoint, volume.rstrip (sep) + sep))

def volumes ():
  hSearch, volume_name = _kernel32.FindFirstVolume ()
  yield Volume (volume_name)
  while True:
    volume_name = _kernel32.FindNextVolume (hSearch)
    if volume_name is None:
      break
    else:
      yield Volume (volume_name)

def mounts ():
  for v in volumes ():
    for m in v.mounts:
      yield Dir (m), v

class Entry (core._WinSysObject):
  
  def __init__ (self, filepath):
    if isinstance (filepath, FilePath):
      self.name = filepath.filename
      self._real_filepath = filepath
      self._filepath = unicode (filepath)
    else:
      pieces = _get_parts (filepath)
      self.name = pieces[-1] or (pieces[-2] + sep)
      self._real_filepath = None
      self._filepath = "".join (pieces[:2]) + sep.join (pieces[2:])

  def dumped (self, level=0):
    output = []
    output.append (unicode (self.filepath))
    output.append (self.filepath.dumped (level))
    output.append ("readable: %s" % self.readable)
    if self.readable:
      output.append ("id: %s" % self.id)
      output.append ("n_links: %s" % self.n_links)
      output.append ("created_at: %s" % self.created_at)
      output.append ("accessed_at: %s" % self.accessed_at)
      output.append ("written_at: %s" % self.written_at)
      output.append ("uncompressed_size: %s" % self.uncompressed_size)
      output.append ("size: %s" % self.size)
    output.append ("Attributes:")
    output.append (self.attributes.dumped (level))
    try:
      s = self.security ()
    except win32file.error, (errno, errctx, errmsg):
      if errno == winerror.ERROR_ACCESS_DENIED:
        pass
    else:
      output.append ("Security:\n" + s.dumped (level))
    return utils.dumped ("\n".join (output), level)
  
  def _get_readable (self):
    try:
      with Handle (self._filepath): pass
    except:
      return False
    else:
      return True
  readable = property (_get_readable)
      
  #
  # Keep filepath as a lazy lookup because it
  # *severely* slows down the file iterations.
  #
  def _get_filepath (self):
    if self._real_filepath is None:
      self._real_filepath = FilePath (self._filepath)
    return self._real_filepath
  filepath = property (_get_filepath)
  
  def _get_created_at (self):
    return utils.from_pytime (wrapped (win32file.GetFileAttributesEx, self._filepath)[1])
  def _set_created_at (self, created_at, handle=None):
    with Handle (handle or self._filepath, True) as handle:
      created_at = pywintypes.Time (time.mktime (created_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, created_at, None, None)
  created_at = property (_get_created_at, _set_created_at)
  
  def _get_accessed_at (self):
    return utils.from_pytime (wrapped (win32file.GetFileAttributesEx, self._filepath)[2])
  def _set_accessed_at (self, accessed_at, handle=None):
    with Handle (handle or self._filepath, True) as handle:
      accessed_at = pywintypes.Time (time.mktime (accessed_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, None, accessed_at, None)
  accessed_at = property (_get_accessed_at, _set_accessed_at)
  
  def _get_written_at (self):
    return utils.from_pytime (wrapped (win32file.GetFileAttributesEx, self._filepath)[3])
  def _set_written_at (self, written_at, handle=None):
    with Handle (handle or self._filepath, True) as handle:
      written_at = pywintypes.Time (time.mktime (written_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, None, None, written_at)
  written_at = property (_get_written_at, _set_written_at)
  
  def _get_uncompressed_size (self, handle=None):
    with Handle (handle or self._filepath) as handle:
      return wrapped (win32file.GetFileSize, handle)
  uncompressed_size = property (_get_uncompressed_size)
  
  def _get_size (self):
    return wrapped (win32file.GetCompressedFileSize, utils.normalised (self._filepath))
  size = property (_get_size)
  
  def _get_attributes (self):
    return Attributes (wrapped (win32file.GetFileAttributesEx, utils.normalised (self._filepath))[0])
  attributes = property (_get_attributes)
  
  def _get_id (self):
    with Handle (self._filepath) as hFile:
      file_information = wrapped (win32file.GetFileInformationByHandle, hFile)
      volume_serial_number = file_information[4]
      index_lo, index_hi = file_information[8:10]
      return volume_serial_number + (utils._longword (index_lo, index_hi) * 2 << 31)
  id = property (_get_id)
  
  def _get_n_links (self):
    with Handle (self._filepath) as hFile:
      file_information = wrapped (win32file.GetFileInformationByHandle, hFile)
      return file_information[7]
  n_links = property (_get_n_links)

  def _set_file_attribute (self, key, value):
    attr = FILE_ATTRIBUTE[key.upper ()]
    if value:
      wrapped (win32file.SetFileAttributesW, utils.normalised (self._filepath), self.attributes.flags | attr)
    else:
      wrapped (win32file.SetFileAttributesW, utils.normalised (self._filepath), self.attributes.flags & ~attr)
      
  def _get_archive (self):
    return self.attributes.archive
  def _set_archive (self, value):
    self._set_file_attribute ("archive", value)
  archive = property (_get_archive, _set_archive)
  
  def _get_compressed (self):
    return self.attributes.compressed
  compressed = property (_get_compressed)
  
  def _get_directory (self):
    return self.attributes.directory
  directory = property (_get_directory)
  
  def _get_encrypted (self):
    return self.attributes.encrypted
  encrypted = property (_get_encrypted)
  
  def _get_hidden (self):
    return self.attributes.hidden
  def _set_hidden (self, value):
    self._set_file_attribute (u"hidden", value)
  hidden = property (_get_hidden, _set_hidden)
  
  def _get_normal (self):
    return self.attributes.normal
  def _set_normal (self, value):
    wrapped (win32file.SetFileAttributesW, utils.normalised (self._filepath), FILE_ATTRIBUTE.NORMAL)
  hidden = property (_get_hidden, _set_hidden)
  
  def _get_not_content_indexed (self):
    return self.attributes.not_content_indexed
  def _set_not_content_indexed (self, value):
    self._set_file_attribute (u"not_content_indexed", value)
  not_content_indexed = property (_get_not_content_indexed, _set_not_content_indexed)
  
  def _get_offline (self):
    return self.attributes.offline
  def _set_offline (self, value):
    self._set_file_attribute (u"offline", value)
  offline = property (_get_offline, _set_offline)
  
  def _get_readonly (self):
    return self.attributes.readonly
  def _set_readonly (self, value):
    self._set_file_attribute (u"readonly", value)
  readonly = property (_get_readonly, _set_readonly)
  
  def _get_reparse_point (self):
    return self.attributes.reparse_point
  reparse_point = property (_get_reparse_point)
  
  def _get_sparse_file (self):
    return self.attributes.sparse_file
  sparse_file = property (_get_sparse_file)
  
  def _get_system (self):
    return self.attributes.system
  def _set_system (self, value):
    self._set_file_attribute (u"system", value)
  system = property (_get_system, _set_system)
  
  def _get_temporary (self):
    return self.attributes.temporary
  def _set_temporary (self, value):
    self._set_file_attribute (u"temporary", value)
  temporary = property (_get_temporary, _set_temporary)
  
  def _get_virtual (self):
    return self.attributes.virtual
  virtual = property (_get_virtual)
  
  def as_string (self):
    return self._filepath.encode ("utf8")
  
  def __unicode__ (self):
    return self._filepath
    
  def __eq__ (self, other):
    return self._filepath.lower () == unicode (other).lower ()
    
  def __lt__ (self, other):
    return self._filepath.lower () < unicode (other).lower ()

  def __nonzero__ (self):
    u"""Determine whether the file exists (at least from
    the POV of the current user) on the filesystem so that
    it can be checked with if fs.file ("..."):
    """
    return (wrapped (win32file.GetFileAttributesW, utils.normalised (self._filepath)) != -1)
  
  def parent (self):
    if self.filepath.parent:
      return Dir (self.filepath.parent)
    else:
      raise x_no_such_file (u"%s has no parent" % self)
    
  def ancestors (self):
    try:
      parent = self.parent ()
    except x_no_such_file:
      raise StopIteration
    else:
      yield parent
      for ancestor in parent.ancestors ():
        yield ancestor

  def security (self, options=security.Security.DEFAULT_OPTIONS):
    return security.security (self._filepath, options=options)
    
  def compress (self):
    with Handle (self._filepath, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.DEFAULT)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
  
  def uncompress (self):
    with Handle (self._filepath, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.NONE)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      
  def encrypt (self):
    wrapped (win32file.EncryptFile, self._filepath)

  def decrypt (self):
    wrapped (win32file.DecryptFile (self._filepath))
  
  def query_encryption_users (self):
    return [(principal (sid), hashblob, info) for (sid, hashblob, info) in wrapped (win32file.QueryUsersOnEncryptedFile, self._filepath)]
  
  def move (self, other, callback=None, callback_data=None):
    return move (self._filepath, unicode (other), callback, callback_data)
    
  def take_ownership (self):
    """Set the new owner of the file to be the logged-on user.
    This is no more than a slight shortcut to the equivalent
    security operations.
    """
    #
    # Specify no options when reading as we may have no rights 
    # whatsoever on the security descriptor and be relying on
    # the take_ownership privilege.
    #
    with self.security (options=0) as s:
      s.owner = security.Principal.me ()
    
class File (Entry):

  ##
  ## 3 ways in which 2 files can be equal:
  ##   Their filepaths are equal
  ##   Their ids (inodes) are equal
  ##   Their contents are equal
  ##
  
  def create (self, security=None):
    pass
  
  def delete (self):
    return delete (self._filepath)
    
  def copy (self, other, callback=None, callback_data=None):
    other_file = file (other)
    if other_file and other_file.directory:
      other = os.path.join (other, self.filepath.filename)
    return copy (self._filepath, unicode (other), callback, callback_data)
    
  def equal_contents (self, other):
    return self == other or filecmp.cmp (self._filepath, other.filepath)
    
  def hard_link_to (self, other):
    return wrapped (win32file.CreateHardLink, utils.normalised (unicode (other)), utils.normalised (self._filepath))
    
  def hard_link_from (self, other):
    return wrapped (win32file.CreateHardLink, utils.normalised (self._filepath), utils.normalised (unicode (other)))
    
  def touch (self):
    return touch (self.filepath)
    
class Dir (Entry):
  
  def __init__ (self, filepath, *args, **kwargs):
    Entry.__init__ (self, filepath.rstrip (seps) + sep, *args, **kwargs)
    parts = _get_parts (self._filepath)
    self.name = parts[-1] + sep
  
  def compress (self, apply_to_contents=True, callback=None):
    Entry.compress (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          if callback: callback (dir)
          dir.compress (False)
        for file in files:
          if callback: callback (file)
          file.compress ()
  
  def uncompress (self, apply_to_contents=True, callback=None):
    Entry.uncompress (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          if callback: callback (dir)
          dir.uncompress (False)
        for file in files:
          if callback: callback (file)
          file.uncompress ()
          
  def encrypt (self, apply_to_contents=True):
    Entry.encrypt (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          dir.encrypt (False)
        for file in files:
          file.encrypt ()
  
  def decrypt (self, apply_to_contents=True):
    Entry.decrypt (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          dir.decrypt (False)
        for file in files:
          file.decrypt ()
          
  def disable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._filepath, True)
  
  def enable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._filepath, False)
    
  def create (self, security=None):
    mkdir (self._filepath, security)
    
  def flat (self, *args, **kwargs):
    return flat (self._filepath, *args, **kwargs)

  def files (self, *args, **kwargs):
    return (f for f in files (os.path.join (self._filepath, u"*"), *args, **kwargs) if not f.directory)
    
  def dirs (self):
    return (f for f in files (os.path.join (self._filepath, u"*")) if f.directory)
      
  def walk (self, *args, **kwargs):
    for dirpath, dirs, files in walk (self._filepath, *args, **kwargs):
      yield dirpath, dirs, files
  
  def mounted_by (self):
    for dir, vol in mounts ():
      if dir == self:
        return vol
  
  def mount (self, vol):
    for f in self.flat (includedirs=True):
      raise x_fs (u"You can't mount to a non-empty directory")
    else:
      mount (self, vol)
      
  def dismount (self):
    dismount (self)
  
  def copy (self, target_filepath, callback=None):
    target = file (target_filepath.rstrip (sep) + sep)
    if target and not target.directory:
      raise x_no_such_file (u"%s exists but is not a directory")
    if not target:
      target.create ()
    
    for dirpath, dirs, files in self.walk ():
      
      for d in dirs:
        target_dir = Dir (target.filepath + d.filepath.relative_to (self.filepath))
        if callback: 
          if not callback (target_dir):
            continue
        target_dir.create ()
      
      for f in files:
        target_file = File (target.filepath + f.filepath.relative_to (self.filepath))
        if callback:
          if not callback (target_file):
            continue
        f.copy (target_file)
  
  def delete (self, recursive=False, callback=None):
    if recursive:
      for f in self.flat (depthfirst=True, includedirs=True):
        if callback:
          callback (f.filepath)
        f.delete ()
    rmdir (self._filepath)
    
  def watch (self, *args, **kwargs):
    watch (self._filepath, *args, **kwargs)

def files (pattern="*", ignore=[u".", u".."], ignore_access_errors=False):
  parts = _get_parts (unicode (pattern))
  dirpath = parts[0] + parts[1] + sep.join (parts[2:-1])
  try:
    iterator = wrapped (win32file.FindFilesIterator, pattern)
  except exceptions.x_access_denied:
    if ignore_access_errors:
      core.warn ("Ignored access error on first iteration of %s", pattern)
      raise StopIteration
    else:
      raise
  except x_no_such_file:
    #
    # If this occurs, it means there's a bizarre problem
    # with a filename windows won't handle. Just stop
    # iteration.
    #
    core.warn ("Ignored no-such-file on first iteration of %s", pattern)
    raise StopIteration

  while True:
    try:
      f = iterator.next ()
      filename = f[8]
      if filename not in ignore:
        if f[0] & FILE_ATTRIBUTE.DIRECTORY:
          yield Dir (os.path.join (dirpath, filename))
        else:
          yield File (os.path.join (dirpath, filename))
    except StopIteration:
      break
    except exceptions.x_access_denied:
      if ignore_access_errors:
        core.warn ("Ignored access error on later iteration of %s", pattern)
        continue
      else:
        raise
    except x_no_such_file:
      #
      # If this occurs, it means there's a bizarre problem
      # with a filename windows won't handle. Just stop
      # iteration.
      #
      core.warn ("Ignored no-such-file on first iteration of %s", pattern)
      raise StopIteration

def file (filepath, ignore_access_errors=False):
  
  def _guess (filepath):
    u"""If the path doesn't exist on the filesystem,
    guess whether it's intended to be a dir or a file
    by looking for a trailing slash.
    """
    parts = _get_parts (filepath)
    if parts[-1]:
      return File (filepath)
    else:
      return Dir (filepath)
  
  if filepath is None:
    return None
  elif isinstance (filepath, Entry):
    return filepath
  else:
    try:
      for f in files (filepath, ignore_access_errors=ignore_access_errors):
        return f
      else:
        return _guess (filepath)
    except x_no_such_file:
      return _guess (filepath)
      
def dir (filepath, ignore_access_errors=False):
  f = file (filepath, ignore_access_errors=ignore_access_errors)
  if isinstance (f, Dir):
    return f
  elif isinstance (f, File):
    raise x_fs, (u"%s exists and is not a directory" % filepath)
  else:
    return Dir (filepath)

def glob (pattern, ignore_access_errors=False):
  dirname = os.path.dirname (pattern)
  return (entry.filepath for entry in files (pattern, ignore_access_errors=False))

def listdir (dir, ignore_access_errors=False):
  pattern = FilePath (dir.rstrip (seps)) + u"*"
  try:
    return (f.name for f in files (pattern, ignore_access_errors=ignore_access_errors))
  except win32file.error:
    return []

def walk (top, depthfirst=False, ignore_access_errors=False):
  top = file (top)
  dirs, nondirs = [], []
  root = os.path.join (unicode (top), u"*")
  for f in files (root, ignore_access_errors=ignore_access_errors):
    if isinstance (f, Dir):
      dirs.append (f)
    else:
      nondirs.append (f)

  if not depthfirst: yield top, dirs, nondirs
  for dir in dirs:
    for x in walk (dir, depthfirst=depthfirst, ignore_access_errors=ignore_access_errors):
      yield x
  if depthfirst: yield top, dirs, nondirs

def flat (root, pattern="*", includedirs=False, depthfirst=False, ignore_access_errors=False):
  walker = walk (
    utils.normalised (root.rstrip (seps) + sep),
    depthfirst=depthfirst, 
    ignore_access_errors=ignore_access_errors
  )
  for dirpath, dirs, files in walker:
    if includedirs:
      for dir in dirs:
        if fnmatch.fnmatch (dir.name, pattern):
          yield dir
    for file in files:
      if fnmatch.fnmatch (file.name, pattern):
        yield file

def progress_wrapper (callback):
  
  def _progress_wrapper (
    TotalFileSize, TotalBytesTransferred, 
    StreamSize, StreamBytesTransferred, StreamNumber, 
    CallbackReason,
    SourceFile, DestinationFile,
    data
  ):
    if callback (TotalFileSize, TotalBytesTransferred, data):
      return PROGRESS.CANCEL
    else:
      return PROGRESS.CONTINUE
  
  if callback:
    return _progress_wrapper
  else:
    return None

def move (source_filepath, target_filepath, callback=None, callback_data=None, clobber=0):
  flags = MOVEFILE.WRITE_THROUGH
  if clobber:
    flags |= MOVEFILE.REPLACE_EXISTING
  wrapped (
    win32file.MoveFileWithProgress,
    utils.normalised (source_filepath), 
    utils.normalised (target_filepath), 
    progress_wrapper (callback), 
    callback_data, 
    flags
  )
  return file (target_filepath)

def copy (source_filepath, target_filepath, callback=None, callback_data=None):
  target_file = file (target_filepath)
  if target_file and target_file.directory:
    target_filepath.join (source_filepath)
  wrapped (
    win32file.CopyFileEx,
    utils.normalised (source_filepath), 
    utils.normalised (target_filepath), 
    progress_wrapper (callback), 
    callback_data
  )
  return file (target_filepath)

def delete (filepath):
  wrapped (win32file.DeleteFileW, utils.normalised (filepath))
  
def rmdir (filepath):
  wrapped (win32file.RemoveDirectory, utils.normalised (filepath))

def attributes (filepath):
  attributes = wrapped (win32file.GetFileAttributesW, utils.normalised (filepath))
  if attributes == -1:
    raise x_no_such_file (u"No such file: %s" % filepath)
  else:
    return Attributes (attributes)

def exists (filepath):
  try:
    attributes (filepath)
  except x_no_such_file:
    return False
  else:
    return True

#
# Module-level convenience functions mapping
# to file/directory attributes.
#
def is_hidden (filepath):
  return attributes (filepath).hidden
  
def is_readonly (filepath):
  return attributes (filepath).readonly
  
def is_system (filepath):
  return attributes (filepath).system
  
def is_archive (filepath):
  return attributes (filepath).archive
  
def is_compressed (filepath):
  return attributes (filepath).compressed
  
def is_encrypted (filepath):
  return attributes (filepath).encrypted
  
def mkdir (dirpath, security=None):
  parts = FilePath (dirpath).parts
  root, pieces = parts[0], parts[1:]
  
  for i, piece in enumerate (pieces):
    path = root + sep.join (pieces[:i+1])
    f = file (path)
    if f:
      if not f.directory:
        raise x_fs (u"%s exists and is not a directory" % f)
    else:
      wrapped (win32file.CreateDirectory, utils.normalised (path), security.pyobject () if security else None)

def touch (filepath, security=None):
  wrapped (
    win32file.CreateFile,
    unicode (filepath),
    GENERIC_ACCESS.WRITE,
    0,
    None if security is None else security.pyobject (),
    FILE_CREATION.OPEN_ALWAYS,
    0,
    None
  ).close ()

def mount (filepath, vol):
  return wrapped (win32file.SetVolumeMountPoint, utils.normalised (filepath) + sep, volume (vol).name)

def dismount (filepath):
  return wrapped (win32file.DeleteVolumeMountPoint, utils.normalised (filepath) + sep)

class _DirWatcher (object):
  
  WATCH_FOR = reduce (operator.or_, FILE_NOTIFY_CHANGE.values ())
  BUFFER_SIZE = 8192
  TIMEOUT = 500
  
  def __init__ (self, root, subdirs=False, watch_for=WATCH_FOR, buffer_size=BUFFER_SIZE):
    self.root = root
    self.subdirs = subdirs
    self.watch_for = watch_for
    self.overlapped = wrapped (pywintypes.OVERLAPPED)
    self.overlapped.hEvent = wrapped (win32event.CreateEvent, None, 0, 0, None)
    self.buffer = wrapped (win32file.AllocateReadBuffer, buffer_size)
    self.hDir = wrapped (
      win32file.CreateFile,
      utils.normalised (root),
      FILE_ACCESS.LIST_DIRECTORY,
      #
      # This must allow RWD otherwises files in
      # the dir will be constrained.
      #
      FILE_SHARE.READ | FILE_SHARE.WRITE | FILE_SHARE.DELETE,
      None,
      FILE_CREATION.OPEN_EXISTING,
      FILE_FLAG.BACKUP_SEMANTICS | FILE_FLAG.OVERLAPPED,
      None
    )
    self._changes = collections.deque ()
    
  def __iter__ (self):
    return self
    
  def next (self):
    try:
      wrapped (win32file.ReadDirectoryChangesW, self.hDir, self.buffer, self.subdirs, self.watch_for, self.overlapped)
    except exceptions.x_invalid_handle:
      raise StopIteration

    while True:
      if wrapped (win32event.WaitForSingleObject, self.overlapped.hEvent, self.TIMEOUT) == win32event.WAIT_OBJECT_0:
        n_bytes = wrapped (win32file.GetOverlappedResult, self.hDir, self.overlapped, True)
        if n_bytes == 0:
          raise StopIteration
      
        last_result = None
        old_file = new_file = None
        for action, filename in wrapped (win32file.FILE_NOTIFY_INFORMATION, self.buffer, n_bytes):
          if action == FILE_ACTION.ADDED:
            new_file = file (os.path.join (self.root, filename))
          elif action == FILE_ACTION.REMOVED:
            old_file = file (os.path.join (self.root, filename))
          elif action == FILE_ACTION.MODIFIED:
            old_file = new_file = file (os.path.join (self.root, filename))
          elif action == FILE_ACTION.RENAMED_OLD_NAME:
            old_file = file (os.path.join (self.root, filename))
            action = None
          elif action == FILE_ACTION.RENAMED_NEW_NAME:
            new_file = file (os.path.join (self.root, filename))

          if action:
            result = (action, old_file, new_file)
            if result <> last_result:
              self._changes.append (result)
      
      if self._changes:
        return self._changes.popleft ()
  
  def stop (self):
    self.hDir.close ()
    
def watch (root, subdirs=False, watch_for=_DirWatcher.WATCH_FOR, buffer_size=_DirWatcher.BUFFER_SIZE):
  return _DirWatcher (root, subdirs, watch_for, buffer_size)

if __name__ == '__main__':
  print "Watching", os.path.abspath (".")
  watcher = watch (".", True)
  try:
    for action, old_filename, new_filename in watcher:
      if action in (FILE_ACTION.ADDED, FILE_ACTION.MODIFIED):
        print "%10s %s %d" % (FILE_ACTION.name_from_value (action), new_filename, file (new_filename).size)
  except KeyboardInterrupt:
    watcher.stop ()
