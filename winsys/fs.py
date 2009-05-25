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
import zipfile

import ntsecuritycon
import pywintypes
import winerror
import win32api
import win32con
import win32event
import win32file
import winioctlcon

if not hasattr (winerror, 'ERROR_BAD_RECOVERY_POLICY'):
  winerror.ERROR_BAD_RECOVERY_POLICY = 6012

from winsys import constants, core, exc, security, utils, _kernel32

sep = unicode (os.sep)
seps = u"/\\"

class x_fs (exc.x_winsys):
  u"Base for all fs-related exceptions"

class x_no_such_file (x_fs):
  u"Raised when a file could not be found"

class x_too_many_files (x_fs):
  u"Raised when more than one file matches a name"
  
class x_invalid_name (x_fs):
  u"Raised when a filename contains invalid characters"
  
class x_no_certificate (x_fs):
  u"Raised when encryption is attempted without a certificate"
  
class x_not_ready (x_fs):
  u"Raised when a device is not ready"
  
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
FILE_ACCESS.doc ("File-specific access rights")
FILE_SHARE = constants.Constants.from_pattern (u"FILE_SHARE_*", namespace=win32file)
FILE_SHARE.doc ("Ways of sharing a file for reading, writing, &c.")
FILE_NOTIFY_CHANGE = constants.Constants.from_pattern (u"FILE_NOTIFY_CHANGE_*", namespace=win32con)
FILE_NOTIFY_CHANGE.doc ("Notification types to watch for when a file changes")
FILE_ACTION = constants.Constants.from_dict (dict (
  ADDED = 1,
  REMOVED = 2,
  MODIFIED = 3,
  RENAMED_OLD_NAME = 4,
  RENAMED_NEW_NAME = 5
))
FILE_ACTION.doc ("Results of a file change")
FILE_ATTRIBUTE = constants.Constants.from_pattern (u"FILE_ATTRIBUTE_*", namespace=win32file)
FILE_ATTRIBUTE.update (dict (
  ENCRYPTED=0x00004000, 
  REPARSE_POINT=0x00000400,
  SPARSE_FILE=0x00000200,
  VIRTUAL=0x00010000,
  NOT_CONTENT_INDEXES=0x00002000,
))
FILE_ATTRIBUTE.doc ("Attributes applying to any file")
PROGRESS = constants.Constants.from_pattern (u"PROGRESS_*", namespace=win32file)
PROGRESS.doc ("States within a file move/copy progress")
MOVEFILE = constants.Constants.from_pattern (u"MOVEFILE_*", namespace=win32file)
MOVEFILE.doc ("Options when moving a file")
FILE_FLAG = constants.Constants.from_pattern (u"FILE_FLAG_*", namespace=win32con)
FILE_FLAG.doc ("File flags")
FILE_CREATION = constants.Constants.from_list ([
  u"CREATE_ALWAYS", 
  u"CREATE_NEW", 
  u"OPEN_ALWAYS", 
  u"OPEN_EXISTING", 
  u"TRUNCATE_EXISTING"
], namespace=win32con)
FILE_CREATION.doc ("Options when creating a file")
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
VOLUME_FLAG.doc ("Characteristics of a volume")
DRIVE_TYPE = constants.Constants.from_pattern (u"DRIVE_*", namespace=win32file)
DRIVE_TYPE.doc ("Types of drive")
COMPRESSION_FORMAT = constants.Constants.from_dict (dict (
  NONE = 0x0000,   
  DEFAULT = 0x0001,   
  LZNT1 = 0x0002
))
COMPRESSION_FORMAT.doc ("Ways in which a file can be compressed")
FSCTL = constants.Constants.from_pattern (u"FSCTL_*", namespace=winioctlcon)
FSCTL.doc ("Types of fsctl operation")

PyHANDLE = pywintypes.HANDLEType

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
  ur"""Return a file handle either for querying
  (the default case) or for writing -- including writing directories
  
  :param filepath: anything whose unicode representation is a valid file path
  :param write: is the handle to be used for writing [True]
  :return: an open file handle for reading or writing, including directories
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
  the filepath, making sure to close it afterwards.
  
  :param handle_or_filepath: an existing handle or something accepted by :func:`handle`
  :param write: passed through to :func:`handle`
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
  are normalised first.
  
  ================ ================ ================
  filepath1        filepath2        result
  ================ ================ ================
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

class FilePath (unicode):
  ur"""A unicode subclass which knows about path structures on Windows.
  The path itself need not exist on any filesystem, but it has to match
  the rules which would make it possible.
  
  FilePaths can be absolute or relative. The only difference is that
  the root attribute is empty for relative paths. They can be added
  to each other or to other unicode strings which will use os.path.join
  semantics.
  
  A FilePath offers quick access to the different parts of the path:
  
  * parts - a list of the components (cf :func:`fs.get_parts`)
  * root - the drive or UNC server/share ending in a backslash unless a drive-relative path
  * filename - final component (may be blank if the path looks like a directory)
  * name - same as filename unless blank in which case second-last component
  * dirname - all path components before the last
  * path - combination of root and dirname
  * parent - combination of root and all path components before second penultimate
  * base - base part of filename (ie the piece before the dot)
  * ext - ext part of filename (ie the dot and the piece after)

  =================== ========== ========= ========= ========= =========== ========== ===== ====
  Path                root       filename  name      dirname   path        parent     base  ext
  =================== ========== ========= ========= ========= =========== ========== ===== ====
  \\\\a\\b\\c\\d.txt  \\\\a\\b\\ d.txt     d.txt     \\c       \\\\a\\b\\c \\\\a\\b   d     .txt  
  c:\\boot.ini        c:\\       boot.ini  boot.ini  \\        c:\\        c:\\       boot  .ini
  boot.ini                       boot.ini  boot.ini                        x_fs       boot  .ini
  c:\\t               c:\\       t         t         \\        c:\\        c:\\       t         
  c:\\t\\             c:\\                 t         \\        c:\\        c:\\       t
  c:\\t\\a.txt        c:\\       a.txt     a.txt     \\t       c:\\t       c:\\t      a     .txt
  c:a.txt             c:         a.txt     a.txt               c:          x_fs       a     .txt
  =================== ========== ========= ========= ========= =========== ========== ===== ====
  """
  def __new__ (meta, filepath, *args, **kwargs):
    return unicode.__new__ (meta, filepath.lower (), *args, **kwargs)

  def __init__ (self, filepath, *args, **kwargs):
    self._parts = None
    self._root = None
    self._filename = None
    self._name = None
    self._dirname= None
    self._path = None
    self._parent = None
    self._base = None
    self._ext = None
      
  def dump (self, level=0):
    print self.dumped (level=level)
  
  def dumped (self, level=0):
    output = []
    output.append (self)
    output.append (u"parts: %s" % self.parts)
    output.append (u"root: %s" % self.root)
    output.append (u"dirname: %s" % self.dirname)
    output.append (u"name: %s" % self.name)
    output.append (u"path: %s" % self.path)
    output.append (u"filename: %s" % self.filename)
    output.append (u"base: %s" % self.base)
    output.append (u"ext: %s" % self.ext)
    if self.root and self.parent:
      output.append (u"parent: %s" % self.parent)
    return utils.dumped (u"\n".join (output), level)

  def _get_parts (self):
    if self._parts is None:
      self._parts = get_parts (self)
    return self._parts
  parts = property (_get_parts)
  
  def _get_root (self):
    if self._root is None:
      self._root = self.__class__ (self.parts[0])
    return self._root
  root = property (_get_root)
  
  def _get_filename (self):
    if self._filename is None:
      self._filename = self.parts[-1]
    return self._filename
  filename = property (_get_filename)
  
  def _get_dirname (self):
    if self._dirname is None:
      self._dirname = sep.join (self.parts[1:-1])
    return self._dirname
  dirname = property (_get_dirname)
  
  def _get_path (self):
    if self._path is None:
      self._path = self.__class__ (self.root + self.dirname)
    return self._path
  path = property (_get_path)
  
  def _get_parent (self):
    if not self.root:
      raise x_fs (None, "FilePath.parent", "Cannot find parent for relative path")
    if self._parent is None:
      parent_dir = [p for p in self.parts if p][:-1]
      if parent_dir:
        self._parent = self.__class__ (parent_dir[0] + sep.join (parent_dir[1:]))
      else:
        self._parent = None
    return self._parent
  parent = property (_get_parent)
  
  def _get_name (self):
    if self._name is None:
      self._name = self.parts[-1] or self.parts[-2]
    return self._name
  name = property (_get_name)
  
  def _get_base (self):
    if self._base is None:
      self._base = os.path.splitext (self.filename)[0]
    return self._base
  base = property (_get_base)
  
  def _get_ext (self):
    if self._ext is None:
      self._ext = os.path.splitext (self.filename)[1]
    return self._ext
  ext = property (_get_ext)
  
  def __repr__ (self):
    return u'<%s %s>' % (self.__class__.__name__, self)
  
  def __add__ (self, other):
    return self.__class__ (os.path.join (unicode (self), unicode (other)))
  
  def __radd__ (self, other):
    return self.__class__ (os.path.join (unicode (other), unicode (self)))
  
  def relative_to (self, other):
    """Return this filepath as relative to another. cf :func:`utils.relative_to`
    """
    return relative_to (self, unicode (other))
    
  def absolute (self):
    """Return an absolute version of the current FilePath, whether
    relative or not. Use :func:`os.path.abspath` semantics.
    """
    return self.__class__ (os.path.abspath (self))

  def changed (self, root=None, path=None, filename=None, base=None, ext=None):
    """Return a new :class:`FilePath` with one or more parts changed. This is particularly
    convenient for, say, changing the extension of a file or producing a version on
    another path, eg::
    
      from winsys import fs, shell
      
      BACKUP_DRIVE = "D:\\"
      for f in fs.flat (shell.special_folder ("personal"), "*.doc"):
        f.copy (f.filepath.changed (root=BACKUP_DRIVE))
    """
    if root and path:
      raise x_fs (None, "FilePath.changed", "You cannot change root *and* path")
    elif filename and (base or ext):
      raise x_fs (None, "FilePath.changed", "You cannot change filename *and* base or ext")
      
    if ext: ext = "." + ext.lstrip (".")
    parts = self.parts
    _filename = parts[-1]
    _base, _ext = os.path.splitext (_filename)
    if not (base or ext):
      base, ext = os.path.splitext (filename or _filename)
    return self.__class__.from_parts (root or parts[0], path or sep.join (parts[1:-1]), base or _base, ext or _ext)

  @classmethod
  def from_parts (cls, root, path, base, ext):
    ur"""Recreate a filepath from its constituent parts. No real validation is done;
    it is assumed that the parameters are valid parts of a filepath.
    """
    return cls (root + sep.join (os.path.normpath (path).split (os.sep) + [base+ext]))

filepath = FilePath

class _Attributes (core._WinSysObject):
  u"""Simple class wrapper for the list of file attributes
  (readonly, hidden, &c.) It can be accessed by attribute
  access, item access and the "in" operator::
  
    from winsys import fs
    attributes = fs.file (fs.__file__).parent ().attributes
    assert (attributes.directory)
    assert (attributes[fs.FILE_ATTRIBUTE.DIRECTORY])
    assert ("directory" in attributes)
  """  
  def __init__ (self, flags=0):
    self.flags = flags
      
  def __getitem__ (self, item):
    return bool (self.flags & FILE_ATTRIBUTE.constant (item))
  __getattr__ = __getitem__
  __contains__ = __getitem__
  
  def as_string (self):
    return "%08x" % self.flags
  
  def dumped (self, level=0):
    return utils.dumped (
      u"\n".join (u"%s => %s" % (k, bool (self.flags & v)) for k, v in sorted (FILE_ATTRIBUTE.items ())),
      level
    )

class Drive (core._WinSysObject):
  ur"""Wraps a drive litter, offering access to its :meth:`volume` 
  and the ability to :meth:`mount` or :meth:`dismount` it on a particular 
  volume.
  """
  
  def __init__ (self, drive):
    self.name = drive.rstrip (seps).rstrip (":") + ":" + sep
    self.type = wrapped (win32file.GetDriveTypeW, self.name)
    
  def as_string (self):
    return "Drive %s" % self.name
    
  def root (self):
    ur"""Return a :class:`fs.Dir` object corresponding to the
    root directory of this drive.
    """
    return Dir (self.name)
  
  def _get_volume (self):
    try:
      return volume (self.name)
    except x_no_such_file:
      return None
  volume = property (_get_volume)
  
  def mount (self, vol):
    ur"""Mount the specified volume in this drive.
    
    :param vol: anything accepted by :func:`volume`
    :returns: self
    """
    self.root ().mount (vol)
    return self
    
  def dismount (self):
    ur"""Dismount this drive from its volume"""
    self.root ().dismount ()
    return self
  
  def dumped (self, level):
    output = []
    output.append (u"name: %s" % self.name)
    output.append (u"type (DRIVE_TYPE): %s" % DRIVE_TYPE.name_from_value (self.type))
    if self.volume:
      output.append (u"volume:\n%s" % self.volume.dumped (level))
    mount_points = [(mount_point, volume) for (mount_point, volume) in mounts () if mount_point.filepath.startswith (self.name)]
    output.append (u"mount_points:\n%s" % utils.dumped_list ((u"%s => %s" % i for i in mount_points), level))
    return utils.dumped ("\n".join (output), level)

class Volume (core._WinSysObject):
  ur"""Wraps a filesystem volume, giving access to useful
  information such as the filesystem and a list of drives
  mounted on it. Also offers the ability to mount or dismount.
  
  Attributes:
  
  * label
  * serial_number
  * maximum_component_length
  * flags - combination of :const:`VOLUME_FLAG`
  * file_system_name
  * mounts
  """
  
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
    output.append (u"flags (VOLUME_FLAG):\n%s" % utils.dumped_flags (self.flags, VOLUME_FLAG, level))
    output.append (u"file_system_name: %s" % self.file_system_name)
    return utils.dumped (u"\n".join (output), level)
    
  def mount (self, filepath):
    ur"""Mount this volume on a particular filepath
    
    :param filepath: anything accepted by :func:`dir`
    """
    return mount (filepath, self)
    
  def dismount (self, filepath):
    ur"""Dismount this volume from a particular filepath
    
    :param filepath: anything accepted by :func:`dir`
    """
    dir (filepath).dismount ()
        
class Entry (core._WinSysObject):
  ur"""Heart of the fs module. This class is the parent of the
  :class:`Dir` and :class:`File` classes and contains all the
  functionality common to both. It is rarely instantiated itself,
  altho' it's possible to do so.
  
  Attributes:
  
  * readable
  * filepath
  * created_at
  * accessed_at
  * written_at
  * uncompressed_size
  * size
  * attributes
  * id
  * n_links
  * attributes - an :class:`Attributes` object representing combinations of :const:`FILE_ATTRIBUTE`
  
  Common functionality:
  
  * *No* caching is done: all attributes etc. are checked on the filesystem every time
  * Entries compare (eq, lt, etc.) according to their full filepath
  * Entries are True according to their existence on a filesystem
  * The str representation is the filepath utf8-encoded; unicode is the filepath itself
  """
  
  def __init__ (self, filepath):
    if isinstance (filepath, FilePath):
      self.name = filepath.filename
      self._real_filepath = filepath
      self._filepath = unicode (filepath)
    else:
      pieces = get_parts (filepath)
      self.name = pieces[-1] or pieces[-2]
      self._real_filepath = None
      self._filepath = pieces[0] + sep.join (pieces[1:])

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
    return utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._filepath)[1])
  def _set_created_at (self, created_at, handle=None):
    with Handle (handle or self._filepath, True) as handle:
      created_at = pywintypes.Time (time.mktime (created_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, created_at, None, None)
  created_at = property (_get_created_at, _set_created_at)
  
  def _get_accessed_at (self):
    return utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._filepath)[2])
  def _set_accessed_at (self, accessed_at, handle=None):
    with Handle (handle or self._filepath, True) as handle:
      accessed_at = pywintypes.Time (time.mktime (accessed_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, None, accessed_at, None)
  accessed_at = property (_get_accessed_at, _set_accessed_at)
  
  def _get_written_at (self):
    return utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._filepath)[3])
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
    return _kernel32.GetCompressedFileSize (normalised (self._filepath))
  size = property (_get_size)
  
  def _get_attributes (self):
    return _Attributes (wrapped (win32file.GetFileAttributesExW, normalised (self._filepath))[0])
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
      wrapped (win32file.SetFileAttributesW, normalised (self._filepath), self.attributes.flags | attr)
    else:
      wrapped (win32file.SetFileAttributesW, normalised (self._filepath), self.attributes.flags & ~attr)
      
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
    wrapped (win32file.SetFileAttributesW, normalised (self._filepath), FILE_ATTRIBUTE.NORMAL)
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
    ur"""Determine whether the file exists (at least from
    the POV of the current user) on the filesystem so that
    it can be checked with if fs.entry ("..."):
    """
    return (wrapped (win32file.GetFileAttributesW, normalised (self._filepath)) != -1)
  
  def like (self, pattern):
    ur"""Return true if this filename's name (not the path) matches
    `pattern` according to `fnmatch`, eg::
    
      from winsys import fs
      for f in fs.files ():
        if f.directory and f.like ("test_*"):
          print f
    """
    return fnmatch.fnmatch (self.name, pattern)
  
  def relative_to (self, other):
    ur"""Return the part of this entry's filepath which extends beyond
    other's. eg if this is 'c:/temp/abc.txt' and other is 'c:/temp/'
    then return 'abc.txt'. cf :meth:`FilePath.relative_to`
    """
    return self.filepath.relative_to (other)
  
  def parent (self):
    ur"""Return the :class:`Dir` object which represents the directory
    this entry is in.
    
    :returns: :class:`Dir`
    :raises: :exc:`x_no_such_file` if no parent exists (eg because this is a drive root)
    """
    if self.filepath.parent:
      return Dir (self.filepath.parent)
    else:
      raise x_no_such_file (None, u"Entry.parent", u"%s has no parent" % self)
    
  def ancestors (self):
    ur"""Iterate over this entry's ancestors, yielding the :class:`Dir` object
    corresponding to each one.
    """
    try:
      parent = self.parent ()
    except x_no_such_file:
      raise StopIteration
    else:
      yield parent
      for ancestor in parent.ancestors ():
        yield ancestor

  def security (self, options=security.Security.DEFAULT_OPTIONS):
    ur"""Return a :class:`security.Security` object corresponding to this
    entry's security attributes. Note that the returning object is a context
    manager so a common pattern is::

      #
      # Find all private key files and ensure that only
      # the owner has any access.
      #
      from winsys import fs
      for f in fs.flat ("*.ppk"):
        with f.security () as s:
          s.break_inheritance ()
          s.dacl = [(s.owner, "F", "ALLOW")]
    
    :param options: cf :func:`security.security`
    """
    return security.security (self._filepath, options=options)
    
  def compress (self):
    ur"""Compress this entry; if it is a file, it will be compressed, if it
    is a directory it will be marked so that any new files added to it will
    be compressed automatically.
    """
    with Handle (self._filepath, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.DEFAULT)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      return self
  
  def uncompress (self):
    ur"""Uncompress this entry; if it is a file, it will be uncompressed, if it
    is a directory it will be marked so that any new files added to it will
    not be compressed automatically.
    """
    with Handle (self._filepath, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.NONE)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      return self
      
  def encrypt (self):
    ur"""FIXME: Need to work out how to create certificates for this
    """
    wrapped (win32file.EncryptFile, self._filepath)
    return self

  def decrypt (self):
    ur"""FIXME: Need to work out how to create certificates for this
    """
    wrapped (win32file.DecryptFile (self._filepath))
    return self
  
  def query_encryption_users (self):
    ur"""FIXME: Need to work out how to create certificates for this
    """
    return [
      (principal (sid), hashblob, info) 
        for (sid, hashblob, info) 
        in wrapped (win32file.QueryUsersOnEncryptedFile, self._filepath)
    ]
  
  def move (self, other, callback=None, callback_data=None, clobber=False):
    ur"""Move this entry to the file/directory represented by other.
    If other is a directory, self is copied into it (not over it)
    
    :param other: anything accepted by :func:`entry`
    :param callback: a function which will receive a total size & total transferred
    :param callback_data: passed as extra data to callback
    :param clobber: whether to overwrite the other file if it exists
    """
    other_file = entry (other)
    if other_file and other_file.directory:
      target_filepath = other_file.filepath + self.filepath.filename
    else:
      target_filepath = other_file.filepath
    flags = MOVEFILE.WRITE_THROUGH
    if clobber:
      flags |= MOVEFILE.REPLACE_EXISTING
    wrapped (
      win32file.MoveFileWithProgress,
      self._filepath, 
      normalised (target_filepath),
      progress_wrapper (callback), 
      callback_data, 
      flags
    )
    return file (target_filepath)
    
  def take_control (self, principal=core.UNSET):
    """Give the logged-on user full control to a file. This may
    need to be preceded by a call to :func:`take_ownership` so that the
    user gains WRITE_DAC permissions.
    
    :param principal: anything accepted by :func:`principal` [logged-on user]
    """
    if principal is core.UNSET:
      principal = security.me ()
    #
    # Specify only DACL when reading as we may have no more rights 
    # than that, and we don't need any more.
    #
    with self.security (options="D") as s:
      s.dacl.append ((principal, "F", "ALLOW"))

  def take_ownership (self, principal=core.UNSET):
    """Set the new owner of the file to be the logged-on user.
    This is no more than a slight shortcut to the equivalent
    security operations.
    
    If you specify a principal (other than the logged-in user,
    the default) you may need to have enabled SE_RESTORE privilege.
    Even the logged-in user may need to have enabled SE_TAKE_OWNERSHIP
    if that user has not been granted the appropriate security by
    the ACL.
    
    :param principal: anything accepted by :func:`principal` [logged-on user]
    """
    if principal is core.UNSET:
      principal = security.me ()
    #
    # Specify no options when reading as we may have no rights 
    # whatsoever on the security descriptor and be relying on
    # the take_ownership privilege.
    #
    with self.security (options=0) as s:
      s.owner = principal
    
class File (Entry):

  ##
  ## 3 ways in which 2 files can be equal:
  ##   Their filepaths are equal
  ##   Their ids (inodes) are equal
  ##   Their contents are equal
  ##
  
  def delete (self):
    ur"""Delete this file"""
    wrapped (win32file.DeleteFileW, self._filepath)
    return self

  def copy (self, other, callback=None, callback_data=None):
    ur"""Copy this file to another file or directory. If other is
    a directory, this file is copied into it, otherwise this file
    is copied over it.    
    
    :param other: anything accepted by :func:`entry`
    :param callback: function receiving total size, total so far, callback_data
    :param callback_data: passed to callback
    :returns: :class:`File` object representing other
    """
    other_file = entry (other)
    if other_file and other_file.directory:
      target_filepath = other_file.filepath + self.filepath.filename
    else:
      target_filepath = other_file.filepath
    wrapped (
      win32file.CopyFileEx,
      self.filepath, 
      target_filepath,
      progress_wrapper (callback), 
      callback_data
    )
    return file (target_filepath)
    
  def equal_contents (self, other):
    ur"""Is this file equal in contents to another? Uses the stdlib
    filecmp function which bales out as soon as it can.
    
    :param other: anything accepted by :func:`entry`
    :returns: True if the contents match, False otherwise
    """
    other = entry (other)
    return self == other or filecmp.cmp (self._filepath, other.filepath)
    
  def hard_link_to (self, other):
    ur"""Create other as a hard link to this file.
    
    :param other: anything accepted by :func:`file`
    :returns: :class:`File` object corresponding to other
    """
    other = file (other)
    wrapped (
      win32file.CreateHardLink, 
      normalised (other),
      normalised (self._filepath)
    )
    return other
    
  def hard_link_from (self, other):
    ur"""Create this file as a hard link from other
    
    :param other: anything accepted by :func:`file`
    :returns: this :class:`File` object
    """
    other = file (other)
    wrapped (
      win32file.CreateHardLink, 
      normalised (self._filepath), 
      normalised (other._filepath)
    )
    return self

  def create (self, security=None):
    ur"""Create this file optionally with specific security. If the
    file already exists it will not be overwritten.
    
    :param security: a :class:`security.Security` object
    :returns: this object
    """
    wrapped (
      win32file.CreateFile,
      self._filepath,
      FILE_ACCESS.WRITE,
      0,
      None if security is None else security.pyobject (),
      FILE_CREATION.OPEN_ALWAYS,
      0,
      None
    ).close ()
    return self
  
  def zip (self, zip_filename=core.UNSET, mode="w", compression=zipfile.ZIP_DEFLATED):
    ur"""Zip the file up into a zipfile. By default, the zipfile will have the
    name of the file with ".zip" appended and will be a sibling of the file.
    Also by default a new zipfile will be created, overwriting any existing one, and
    standard compression will be used. The filename will be stored without any directory
    information.
    
    A different zipfile can be specific as the zip_filename parameter, and this
    can be appended to (if it exists) by specifying "a" as the mode param.
    
    The created / appended zip file is returned.
    """
    if zip_filename is core.UNSET:
      zip_filename = self.filepath.changed (ext=".zip")
    
    z = zipfile.ZipFile (zip_filename, mode=mode, compression=compression)
    z.write (self.filepath.filename)
    z.close ()
      
    return file (zip_filename)
  
  touch = create
    
class Dir (Entry):
  
  def __init__ (self, filepath, *args, **kwargs):
    Entry.__init__ (self, filepath.rstrip (seps) + sep, *args, **kwargs)
  
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
    
    return self
  
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
          
    return self
          
  def encrypt (self, apply_to_contents=True):
    Entry.encrypt (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          dir.encrypt (False)
        for file in files:
          file.encrypt ()
          
    return self
  
  def decrypt (self, apply_to_contents=True):
    Entry.decrypt (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          dir.decrypt (False)
        for file in files:
          file.decrypt ()
    
    return self
          
  def disable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._filepath, True)
    return self
  
  def enable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._filepath, False)
    return self

  def create (self, security=None):
    parts = self.filepath.parts
    root, pieces = parts[0], parts[1:]
    
    for i, piece in enumerate (pieces):
      path = root + sep.join (pieces[:i+1])
      f = entry (path)
      if f:
        if not f.directory:
          raise x_fs (None, "Dir.create", u"%s exists and is not a directory" % f)
      else:
        wrapped (
          win32file.CreateDirectory, 
          normalised (path), 
          security.pyobject () if security else None
        )
    
    return Dir (normalised (path))
    
  def entries (self, pattern=u"*", *args, **kwargs):
    return files (os.path.join (self._filepath, pattern), *args, **kwargs)
    
  def file (self, name):
    return file (os.path.join (self._filepath, name))
    
  def dir (self, name):
    return dir (os.path.join (self._filepath, name))
  
  def files (self, pattern=u"*", *args, **kwargs):
    return (f for f in self.entries (pattern, *args, **kwargs) if isinstance (f, File))
    
  def dirs (self, pattern=u"*", *args, **kwargs):
    return (f for f in self.entries (pattern, *args, **kwargs) if isinstance (f, Dir))

  def walk (self, depthfirst=False, ignore_access_errors=False):
    top = self
    dirs, nondirs = [], []
    for f in self.entries (ignore_access_errors=ignore_access_errors):
      if isinstance (f, Dir):
        dirs.append (f)
      else:
        nondirs.append (f)

    if not depthfirst: yield top, dirs, nondirs
    for d in dirs:
      for x in d.walk (depthfirst=depthfirst, ignore_access_errors=ignore_access_errors):
        yield x
    if depthfirst: yield top, dirs, nondirs

  def flat (self, pattern="*", includedirs=False, depthfirst=False, ignore_access_errors=False):
    walker = self.walk (
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

  def mounted_by (self):
    for dir, vol in mounts ():
      if dir == self:
        return vol
  
  def mount (self, vol):
    for f in self.flat (includedirs=True):
      raise x_fs (None, "Dir.mount", u"You can't mount to a non-empty directory")
    else:
      wrapped (win32file.SetVolumeMountPoint, self.filepath, volume (vol).name)    
      return self
      
  def dismount (self):
    wrapped (win32file.DeleteVolumeMountPoint, self.filepath)
    return self
  
  def copy (self, target_filepath, callback=None, callback_data=None):
    """
    Copies associated file to directory specified by 'target_filepath' 
    and returns Dir object. Pass the relative or full directory 
    of target location.    
    """
    target = entry (target_filepath.rstrip (sep) + sep)
    if target and not target.directory:
      raise x_no_such_file (None, "Dir.copy", u"%s exists but is not a directory")
    if not target:
      target.create ()
    
    for dirpath, dirs, files in self.walk ():
      for d in dirs:
        target_dir = Dir (target.filepath + d.relative_to (self.filepath))
        target_dir.create ()
      for f in files:
        target_file = File (target.filepath + f.relative_to (self.filepath))
        f.copy (target_file, callback, callback_data)
  
  def delete (self, recursive=False):
    """
    deletes associated dir
    """
    if recursive:
      for dirpath, dirs, files in self.walk (depthfirst=True, includedirs=True):
        for d in dirs:
          d.delete (recursive=True)
        for f in files:
          f.delete ()
    
    wrapped (win32file.RemoveDirectory, self._filepath)
    return self
    
  def watch (self, *args, **kwargs):
    watch (self._filepath, *args, **kwargs)
    
  def zip (self, zip_filename=core.UNSET, mode="w", compression=zipfile.ZIP_DEFLATED):
    """Zip the directory up into a zip file. By default, the file will have the
    name of the directory with ".zip" appended and will be a sibling of the directory.
    Also by default a new zipfile will be created, overwriting any existing one, and
    standard compression will be used. Filenames are stored as relative to this dir.
    
    A different zip filename can be specific as the zip_filename parameter, and this
    can be appended to (if it exists) by specifying "a" as the mode param.
    
    The created / appended zip file is returned.
    """
    if zip_filename is core.UNSET:
      zip_filename = os.path.join (self.filepath.parent, self.filepath.name + u".zip")
    
    z = zipfile.ZipFile (zip_filename, mode=mode, compression=compression)
    try:
      for f in self.flat ():
        z.write (f.filepath, f.relative_to (self.filepath))
    finally:
      z.close ()
      
    return file (zip_filename)
    
  rmdir = delete
  mkdir = create

def files (pattern="*", ignore=[u".", u".."], ignore_access_errors=False):
  #
  # special-case "." and ".."
  #
  if pattern in (".", ".."):
    pattern = os.path.abspath (pattern)
  try:
    iterator = wrapped (win32file.FindFilesIterator, pattern)
  except exc.x_access_denied:
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

  parts = get_parts (unicode (pattern))
  dirpath = parts[0] + sep.join (parts[1:-1])
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
    except exc.x_access_denied:
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

def entry (filepath, ignore_access_errors=False):
  ur"""Return a :class:`File` or :class:`Dir` object representing this
  filepath.
  
  ======================================= ==================================================
  filepath                                Result
  ======================================= ==================================================
  :const:`None`                           :const:`None`
  an :class:`Entry` or subclass object    the same object
  an existing file                        a :class:`File` object representing that file
  an existing directory                   a :class:`Dir` object representing that directory
  a file which doesn't exist              a :class:`Dir` if filepath ends with \\, 
                                          :class:`File` otherwise
  ======================================= ==================================================
  """
  def _guess (filepath):
    ur"""If the path doesn't exist on the filesystem,
    guess whether it's intended to be a dir or a file
    by looking for a trailing slash.
    """
    parts = get_parts (filepath)
    if parts[-1]:
      return File (filepath)
    else:
      return Dir (filepath)

  if filepath is None:
    return None
  elif isinstance (filepath, Entry):
    return filepath
  else:
    attributes = wrapped (win32file.GetFileAttributesW, filepath)
    if attributes == -1:
      return _guess (filepath)
    elif attributes & FILE_ATTRIBUTE.DIRECTORY:
      return Dir (filepath)
    else:
      return File (filepath)
      
def file (filepath, ignore_access_errors=False):
  ur"""Return a :class:`File` object representing this filepath on
  the filepath. If filepath is already a :class:`File` object, return
  it unchanged otherwise ensure that the filepath doesn't point to
  an existing directory and return a :class:`File` object which
  represents it.
  """
  f = entry (filepath, ignore_access_errors=ignore_access_errors)
  if isinstance (f, File):
    return f
  elif isinstance (f, Dir) and f:
    raise x_fs, (None, u"file", u"%s exists but is a directory" % filepath)
  else:
    return File (filepath)

def dir (filepath, ignore_access_errors=False):
  ur"""Return a :class:`Dir` object representing this filepath on
  the filepath. If filepath is already a :class:`Dir` object, return
  it unchanged otherwise ensure that the filepath doesn't point to
  an existing file and return a :class:`Dir` object which
  represents it.
  """
  f = entry (filepath, ignore_access_errors=ignore_access_errors)
  if isinstance (f, Dir):
    return f
  elif isinstance (f, File) and f:
    raise x_fs (None, u"dir", u"%s exists but is a file" % filepath)
  else:
    return Dir (filepath)

def glob (pattern, ignore_access_errors=False):
  ur"""Mimic the built-in glob.glob functionality as a generator,
  optionally ignoring access errors.
  
  :param pattern: passed to :func:`files`
  :param ignore_access_errors: passed to :func:`files`
  :returns: yields a :class:`FilePath` object for each matching file
  """
  return (entry.filepath for entry in files (pattern, ignore_access_errors=False))

def listdir (d, ignore_access_errors=False):
  ur"""Mimic the built-in os.list functionality as a generator,
  optionally ignoring access errors.
  
  :param d: anything accepted by :func:`dir`
  :param ignore_access_errors: passed to :func:`files`
  :returns: yield the name of each file in directory d
  """
  pattern = dir (d).filepath + u"*"
  try:
    return (f.name for f in files (pattern, ignore_access_errors=ignore_access_errors))
  except win32file.error:
    return []

def walk (root, depthfirst=False, ignore_access_errors=False):
  ur"""Walk the directory tree starting from root, optionally ignoring
  access errors.
  
  :param root: anything accepted by :func:`dir`
  :param depthfirst: passed to :meth:`Dir.walk`
  :param ignore_access_errors: passed to :meth:`Dir.walk`
  :returns: as :meth:`Dir.walk`
  """
  for w in dir (root).walk (depthfirst, ignore_access_errors):
    yield w

def flat (root, pattern="*", includedirs=False, depthfirst=False, ignore_access_errors=False):
  ur"""Iterate over a flattened version of the directory tree starting
  from root. Implemented via :meth:`Dir.flat` (qv).
  
  :param root: anything accepted by :func:`dir`
  :param pattern: passed to :meth:`Dir.flat`
  :param includedirs: passed to :meth:`Dir.flat`
  :param depthfirst: passed to :meth:`Dir.flat`
  :param ignore_access_errors: passed to :meth:`Dir.flat`
  :returns: as :meth:`Dir.flat`
  """
  for f in dir (root).flat (pattern, includedirs=includedirs, ignore_access_errors=ignore_access_errors):
    yield f

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

def move (source_filepath, target_filepath, callback=None, callback_data=None, clobber=False):
  ur"""Move one :class:`Entry` object to another, implemented via :meth:`Entry.move` (qv)
  
  :param source_filepath: anything accepted by :func:`entry`
  :param target_filepath: passed to :meth:`Entry.move`
  :param callback: passed to :meth:`Entry.move`
  :param callback_data: passed to :meth:`Entry.move`
  :param clobber: passed to :meth:`Entry.move`
  """
  return entry (source_filepath).move (target_filepath, callback, callback_data, clobber)

def copy (source_filepath, target_filepath, callback=None, callback_data=None):
  ur"""Copy one :class:`Entry` object to another, implemented via :meth:`Entry.copy` (qv)
  
  :param source_filepath: anything accepted by :func:`entry`
  :param target_filepath: passed to :meth:`Entry.copy`
  :param callback: passed to :meth:`Entry.copy`
  :param callback_data: passed to :meth:`Entry.copy`
  """
  return entry (source_filepath).copy (target_filepath, callback, callback_data)

def delete (filepath):
  ur"""Deletes a :class:`Entry` object, implemented via :meth:`Entry.delete` (qv)
  
  :param filepath: anything accepted by :func:`entry`
  """
  return entry (filepath).delete ()
  
def rmdir (filepath, recursive=False):
  ur"""Mimic the os.rmdir functionality, optionally recursing
  
  :param filepath: anything accepted by :func:`dir`
  :param recursive: passed to :meth:`Dir.delete`
  """
  return dir (filepath).delete (recursive=recursive)

def attributes (filepath):
  ur"""Return an :class:`Attributes` object representing the file attributes
  of filepath, implemented via :meth:`Entry.attributes`
  
  :param filepath: anything accepted by :func:`entry`
  :returns: an :class:`Attributes` object
  """
  return entry (filepath).attributes

def exists (filepath):
  ur"""Mimic os.path.exists, implemented via the :class:`Entry` boolean mechanism
  
  :param filepath: anything accepted by :func:`entry`
  :returns: :const:`True` if filepath exists, :const:`False` otherwise
  """
  return bool (entry (filepath))

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
  
def is_directory (filepath):
  return attributes (filepath).directory
  
def mkdir (dirpath, security=None):
  ur"""Mimic os.mkdir, implemented via :meth:`Dir.create` (qv)
  """
  return dir (dirpath).create (security)

def touch (filepath, security=None):
  ur"""Update a file's modification time, creating it if it
  does not exist, implemented via :meth:`File.create` (qv)
  
  :param filepath: anything accepted by :func:`file`
  """
  return file (filepath).create (security)

def mount (filepath, vol):
  ur"""Mount vol at filepath, implemented via :meth:`Dir.mount` (qv)
  
  :param filepath: anything accepted by :func:`dir`
  :param vol: passed to :meth:`Dir.mount`
  """
  return dir (filepath).mount (vol)

def dismount (filepath):
  ur"""Dismount the volume at filepath, implemented via :meth:`Dir.dismount` (qv)
  
  :param filepath: anything accepted by :func:`dir`
  """
  return dir (filepath).dismount ()

def zip (filepath, *args, **kwargs):
  ur"""Create and return a zip archive of filepath, implemented via :meth:`Entry.zip` (qv)
  
  :param filepath: anything accepted by :func:`entry`
  """
  return entry (filepath).zip (*args, **kwargs)

def drive (drive):
  ur"""Return a :class:`Drive` object representing drive
  
  ======================================= ==================================================
  drive                                   Result
  ======================================= ==================================================
  :const:`None`                           :const:`None`
  an :class:`Drive` or subclass object    the same object
  a drive letter                          a :class:`Drive` object
  ======================================= ==================================================
  """
  if drive is None:
    return None
  elif isinstance (drive, Drive):
    return drive
  else:
    return Drive (drive)

def drives ():
  ur"""Iterate over all the drive letters in the system, yielding a :class:`Drive` object
  representing each one.
  """
  for drive in wrapped (win32api.GetLogicalDriveStrings).strip ("\x00").split ("\x00"):
    yield Drive (drive)

def volume (volume):
  ur"""Return a :class:`Volume` object corresponding to volume
  
  ======================================= ==================================================
  volume                                  Result
  ======================================= ==================================================
  :const:`None`                           :const:`None`
  an :class:`Volume` or subclass object   the same object
  a volume name \\\\?\\Volume...          a :class:`Volume` object representing that volume
  a directory name                        a :class:`Volume` object representing the volume
                                          at that mountpoint
  ======================================= ==================================================
  """
  if volume is None:
    return None
  elif isinstance (volume, Volume):
    return volume
  elif volume.startswith (ur"\\?\Volume"):
    return Volume (volume)
  else:
    return Volume (wrapped (win32file.GetVolumeNameForVolumeMountPoint, volume.rstrip (sep) + sep))

def volumes ():
  ur"""Iterate over all the volumes in the system, yielding a :class:`Volume` object
  representing each one.
  """
  hSearch, volume_name = _kernel32.FindFirstVolume ()
  yield Volume (volume_name)
  while True:
    volume_name = _kernel32.FindNextVolume (hSearch)
    if volume_name is None:
      break
    else:
      yield Volume (volume_name)

def mounts ():
  ur"""Iterate over all mounted volume mountpoints in the system, yielding a
  (:class:`Dir`, :class:`Volume`) pair for each one, eg::
  
    from winsys import fs
    drive_volumes = dict (fs.mounts ())
  """
  for v in volumes ():
    for m in v.mounts:
      yield Dir (m), v

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
      normalised (root),
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
    wrapped (
      win32file.ReadDirectoryChangesW, 
      self.hDir, 
      self.buffer, 
      self.subdirs, 
      self.watch_for, 
      self.overlapped
    )
    while True:
      if wrapped (
          win32event.WaitForSingleObject, 
          self.overlapped.hEvent, 
          self.TIMEOUT
      ) == win32event.WAIT_OBJECT_0:
        n_bytes = wrapped (win32file.GetOverlappedResult, self.hDir, self.overlapped, True)
        if n_bytes == 0:
          continue

        last_result = None
        old_file = new_file = None
        for action, filename in wrapped (win32file.FILE_NOTIFY_INFORMATION, self.buffer, n_bytes):
          if action == FILE_ACTION.ADDED:
            new_file = entry (os.path.join (self.root, filename))
          elif action == FILE_ACTION.REMOVED:
            old_file = entry (os.path.join (self.root, filename))
          elif action == FILE_ACTION.MODIFIED:
            old_file = new_file = entry (os.path.join (self.root, filename))
          elif action == FILE_ACTION.RENAMED_OLD_NAME:
            old_file = entry (os.path.join (self.root, filename))
            action = None
          elif action == FILE_ACTION.RENAMED_NEW_NAME:
            new_file = entry (os.path.join (self.root, filename))

          if action:
            result = (action, old_file, new_file)
            if result <> last_result:
              self._changes.append (result)
      
      if self._changes:
        return self._changes.popleft ()
  
  def stop (self):
    self.hDir.close ()

def watch (root, subdirs=False, watch_for=_DirWatcher.WATCH_FOR, buffer_size=_DirWatcher.BUFFER_SIZE):
  ur"""Return an iterator which returns a file change on every iteration.
  The file change comes in the form: action, old_filename, new_filename.
  action is one of the :const:`FILE_ACTION` constants, while the filenames
  speak for themselves. The filenames will be the same if the file has been
  updated. If the file is new, old_filename will be None; if it has been
  deleted, new_filename will be None; if it has been renamed, they will
  be different.
  """
  return _DirWatcher (root, subdirs, watch_for, buffer_size)

if __name__ == '__main__':
  print "Watching", os.path.abspath (".")
  watcher = watch (".", True)
  try:
    for action, old_filename, new_filename in watcher:
      if action in (FILE_ACTION.ADDED, FILE_ACTION.MODIFIED):
        print "%10s %s %d" % (FILE_ACTION.name_from_value (action), new_filename, entry (new_filename).size)
  except KeyboardInterrupt:
    watcher.stop ()
