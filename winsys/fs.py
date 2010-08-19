# -*- coding: iso-8859-1 -*-
"""Provide a wrapper around common filesystem operations, including
iterating over the files in a directory structure and copying,
moving and linking them. Wherever possible iterators are used,
making it possible to act on large directory structures without
loading them all into memory.
"""
from __future__ import with_statement
import os, sys
import codecs
import collections
import contextlib
import datetime
import filecmp
import fnmatch
import functools
import msvcrt
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

from winsys import constants, core, exc, security, utils, _kernel32, _change_journal

sep = str (os.sep)
seps = "/\\"

class x_fs (exc.x_winsys):
  "Base for all fs-related exceptions"

class x_no_such_file (x_fs):
  "Raised when a file could not be found"

class x_too_many_files (x_fs):
  "Raised when more than one file matches a name"

class x_invalid_name (x_fs):
  "Raised when a filename contains invalid characters"

class x_no_certificate (x_fs):
  "Raised when encryption is attempted without a certificate"

class x_not_ready (x_fs):
  "Raised when a device is not ready"

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
FILE_SHARE = constants.Constants.from_pattern ("FILE_SHARE_*", namespace=win32file)
FILE_SHARE.doc ("Ways of sharing a file for reading, writing, &c.")
FILE_NOTIFY_CHANGE = constants.Constants.from_pattern ("FILE_NOTIFY_CHANGE_*", namespace=win32con)
FILE_NOTIFY_CHANGE.doc ("Notification types to watch for when a file changes")
FILE_ACTION = constants.Constants.from_dict (dict (
  ADDED = 1,
  REMOVED = 2,
  MODIFIED = 3,
  RENAMED_OLD_NAME = 4,
  RENAMED_NEW_NAME = 5
))
FILE_ACTION.doc ("Results of a file change")
FILE_ATTRIBUTE = constants.Constants.from_pattern ("FILE_ATTRIBUTE_*", namespace=win32file)
FILE_ATTRIBUTE.update (dict (
  ENCRYPTED=0x00004000,
  REPARSE_POINT=0x00000400,
  SPARSE_FILE=0x00000200,
  VIRTUAL=0x00010000,
  NOT_CONTENT_INDEXES=0x00002000,
))
FILE_ATTRIBUTE.doc ("Attributes applying to any file")
PROGRESS = constants.Constants.from_pattern ("PROGRESS_*", namespace=win32file)
PROGRESS.doc ("States within a file move/copy progress")
MOVEFILE = constants.Constants.from_pattern ("MOVEFILE_*", namespace=win32file)
MOVEFILE.doc ("Options when moving a file")
FILE_FLAG = constants.Constants.from_pattern ("FILE_FLAG_*", namespace=win32con)
FILE_FLAG.doc ("File flags")
FILE_CREATION = constants.Constants.from_list ([
  "CREATE_ALWAYS",
  "CREATE_NEW",
  "OPEN_ALWAYS",
  "OPEN_EXISTING",
  "TRUNCATE_EXISTING"
], namespace=win32con)
FILE_CREATION.doc ("Options when creating a file")
VOLUME_FLAG = constants.Constants.from_dict (dict (
  FILE_CASE_SENSITIVE_SEARCH      = 0x00000001,
  FILE_CASE_PRESERVED_NAMES       = 0x00000002,
  FILE_str_ON_DISK            = 0x00000004,
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
), pattern="FILE_*")
VOLUME_FLAG.doc ("Characteristics of a volume")
DRIVE_TYPE = constants.Constants.from_pattern ("DRIVE_*", namespace=win32file)
DRIVE_TYPE.doc ("Types of drive")
COMPRESSION_FORMAT = constants.Constants.from_dict (dict (
  NONE = 0x0000,
  DEFAULT = 0x0001,
  LZNT1 = 0x0002
))
COMPRESSION_FORMAT.doc ("Ways in which a file can be compressed")
FSCTL = constants.Constants.from_pattern ("FSCTL_*", namespace=winioctlcon)
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
  r"""Helper function to regularise a file path and then
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
  c:/t/                         ["c:\\", "t"]
  c:/t/test.txt                 ["c:\\", "t", "test.txt"]
  c:/t/s/test.txt               ["c:\\", "t", "s", "test.txt"]
  c:test.txt                    ["c:", "test.txt"]
  s/test.txt                    ["", "s", "test.txt"]
  \\\\server\\share             ["\\\\server\\share\\", ""]
  \\\\server\\share\\a.txt      ["\\\\server\\share\\", "a.txt"]
  \\\\server\\share\\t\\a.txt   ["\\\\server\\share\\", "t", "a.txt"]
  \\\\?\\c:\test.txt            ["\\\\?\\c:\\", "test.txt"]
  \\\\?\\Volume{xxxx-..}\\t.txt ["\\\\?\Volume{xxxx-..}\\", "t.txt"]
  ============================= ======================================

  The upshot is that the first item in the list returned is
  always the root, one of: a slash-terminated drive/volume/share
  for an absolute path; an empty string for a relative path; or
  a drive-colon for a drive-relative path.

  All other items before the last one represent the directories along
  the way. The last item is the filename or directory name.

  The original filepath can usually be reconstructed as::

    from winsys import fs
    filepath = "c:/temp/abc.txt"
    parts = fs.get_parts (filepath)
    assert parts[0] + "\\".join (parts[1:]) == filepath

  The exception is when a root (UNC or volume) is given without
  a trailing slash. This is added in. Or if a directory is given
  with a trailing slash. This is stripped off.
  """
  filepath = filepath.replace ("/", sep)
  prefix_match = re.match (PREFIX, filepath)

  if prefix_match:
    prefix = prefix_match.group (1)
    rest = filepath[len (prefix):].rstrip (sep)
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
  r"""Convert any path or path-like object into the
  length-unlimited str equivalent. This should avoid
  issues with maximum path length and the like.
  """
  #
  # os.path.abspath will return a sep-terminated string
  # for the root directory and a non-sep-terminated
  # string for all other paths.
  #
  filepath = str (filepath)
  if filepath.startswith (2 * sep):
    return filepath
  else:
    is_dir = filepath[-1] in seps
    abspath = os.path.abspath (filepath)
    return ("\\\\?\\" + abspath) + (sep if is_dir and not abspath.endswith (sep) else "")

def handle (filepath, write=False, attributes=None, sec=None):
  r"""Return a file handle either for querying
  (the default case) or for writing -- including writing directories

  :param filepath: anything whose str representation is a valid file path
  :param write: is the handle to be used for writing [True]
  :param attributes: anything accepted by :const:`FILE_ATTRIBUTE`
  :return: an open file handle for reading or writing, including directories
  """
  attributes = FILE_ATTRIBUTE.constant (attributes)
  if attributes is None:
    attributes = FILE_ATTRIBUTE.NORMAL | FILE_FLAG.BACKUP_SEMANTICS
  return wrapped (
    win32file.CreateFile,
    normalised (filepath),
    (FILE_ACCESS.READ | FILE_ACCESS.WRITE) if write else 0,
    (FILE_SHARE.READ | FILE_SHARE.WRITE) if write else FILE_SHARE.READ,
    sec,
    FILE_CREATION.OPEN_ALWAYS if write else FILE_CREATION.OPEN_EXISTING,
    attributes,
    None
  )

@contextlib.contextmanager
def Handle (handle_or_filepath, write=False):
  r"""Return the handle passed or on newly-created for
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
  r"""Return filepath2 relative to filepath1. Both names
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
  return utils.relative_to (filepath1, filepath2.rstrip (seps) + sep)

class FilePath (str):
  r"""A str subtype which knows about path structures on Windows.
  The path itself need not exist on any filesystem, but it has to match
  the rules which would make it possible.

  FilePaths can be absolute or relative. The only difference is that
  the root attribute is empty for relative paths. They can be added
  to each other or to other str strings which will use os.path.join
  semantics.

  A FilePath offers quick access to the different parts of the path:

  * parts - a list of the components (cf :func:`fs.get_parts`)
  * root - the drive or UNC server/share ending in a backslash unless a drive-relative path
  * filename - final component
  * name - same as filename (convenience)
  * dirname - all path components before the last
  * path - combination of root and dirname
  * parent - combination of root and all path components before second penultimate; raises
    an exception is FilePath is relative.
  * base - base part of filename (ie the piece before the dot)
  * ext - ext part of filename (ie the dot and the piece after)

  =================== ========== ========= ========= ========= =========== =========== ===== ====
  Path                root       filename  name      dirname   path        parent      base  ext
  =================== ========== ========= ========= ========= =========== =========== ===== ====
  \\\\a\\b\\c\\d.txt  \\\\a\\b\\ d.txt     d.txt     c         \\\\a\\b\\c \\\\a\\b\\c d     .txt
  c:\\boot.ini        c:\\       boot.ini  boot.ini  _         c:\\        c:\\        boot  .ini
  boot.ini            _          boot.ini  boot.ini  _         _           x_fs        boot  .ini
  c:\\t               c:\\       t         t         _         c:\\        c:\\        t     _
  c:\\t\\             c:\\       t         t         _         c:\\        c:\\        t     _
  c:\\t\\a.txt        c:\\       a.txt     a.txt     t         c:\\t       c:\\t       a     .txt
  c:a.txt             c:         a.txt     a.txt     _         c:          x_fs        a     .txt
  a.txt               _          a.txt     a.txt     _         _           x_fs        a     .txt
  =================== ========== ========= ========= ========= =========== =========== ===== ====
  """
  def __new__ (meta, filepath):
    fp = str.__new__ (meta, filepath.lower ().replace ("/", sep))
    fp._parts = None
    fp._root = None
    fp._filename = None
    fp._name = None
    fp._dirname= None
    fp._path = None
    fp._parent = None
    fp._base = None
    fp._ext = None
    return fp

  def dump (self, level=0):
    sys.stdout.write (self.dumped (level=level))

  def dumped (self, level=0):
    output = []
    output.append (self)
    output.append ("parts: %s" % self.parts)
    output.append ("root: %s" % self.root)
    output.append ("dirname: %s" % self.dirname)
    output.append ("name: %s" % self.name)
    output.append ("path: %s" % self.path)
    output.append ("filename: %s" % self.filename)
    output.append ("base: %s" % self.base)
    output.append ("ext: %s" % self.ext)
    if self.root and self.parent:
      output.append ("parent: %s" % self.parent)
    return utils.dumped ("\n".join (output), level)

  @classmethod
  def factory (cls, filepath):
    r"""Designed to be redefined in a subclass so that the :meth:`__add__` and :meth:`__radd__`
    methods can return the appropriate type.
    """
    return cls (filepath)

  def __repr__ (self):
    return "<%s %s>" % (self.__class__.__name__, self)

  def __add__ (self, other):
    return self.__class__.factory (os.path.join (str (self), str (other)))

  def __radd__ (self, other):
    return self.__class__.factory (os.path.join (str (other), str (self)))

  def _get_parts (self):
    if self._parts is None:
      self._parts = get_parts (self)
    return self._parts
  parts = property (_get_parts)

  def _get_root (self):
    if self._root is None:
      self._root = self.__class__.factory (self.parts[0]) or ""
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
      self._path = self.__class__.factory (self.root + self.dirname)
    return self._path
  path = property (_get_path)

  def _get_parent (self):
    if self.is_relative ():
      raise x_fs (None, "FilePath.parent", "Cannot find parent for relative path")
    if self._parent is None:
      parent_dir = [p for p in self.parts if p][:-1]
      if parent_dir:
        self._parent = self.__class__.factory (parent_dir[0] + sep.join (parent_dir[1:]))
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

  def is_relative (self):
    r"""A filepath is relative if it has no root or if its
    root is a drive letter only (without a directory backslash)."""
    return not self.root.endswith (sep)

  def relative_to (self, other):
    """Return this filepath as relative to another. cf :func:`utils.relative_to`
    """
    return self.__class__.factory (relative_to (self, str (other)))

  def absolute (self):
    """Return an absolute version of the current FilePath, whether
    relative or not. Use :func:`os.path.abspath` semantics.
    """
    return self.__class__.factory (os.path.abspath (self))
  abspath = absolute

  def changed (self, root=None, dirname=None, filename=None, base=None, infix=None, ext=None):
    """Return a new :class:`FilePath` with one or more parts changed. This is particularly
    convenient for, say, changing the extension of a file or producing a version on
    another path, eg::

      from winsys import fs, shell

      BACKUP_DRIVE = "D:\\"
      for f in fs.flat (shell.special_folder ("personal"), "*.doc"):
        f.copy (f.changed (root=BACKUP_DRIVE))
    """
    if filename and (base or ext or infix):
      raise x_fs (None, "FilePath.changed", "You cannot change filename *and* base or ext or infix")

    if ext: ext = "." + ext.lstrip (".")
    parts = self.parts
    _filename = parts[-1]
    _base, _ext = os.path.splitext (_filename)
    if not (base or ext):
      base, ext = os.path.splitext (filename or _filename)
    if infix:
      base += infix
    return self.__class__.from_parts (root or parts[0], dirname or sep.join (parts[1:-1]), base or _base, ext or _ext)

  @classmethod
  def from_parts (cls, root, dirname, base, ext):
    r"""Recreate a filepath from its constituent parts. No real validation is done;
    it is assumed that the parameters are valid parts of a filepath.
    """
    return cls (root + sep.join (os.path.normpath (dirname).split (sep) + [base+ext]))

filepath = FilePath

class _Attributes (core._WinSysObject):
  """Simple class wrapper for the list of file attributes
  (readonly, hidden, &c.) It can be accessed by attribute
  access, item access and the "in" operator::

    from winsys import fs
    attributes = fs.file (fs.__file__).parent ().attributes
    assert (attributes.directory)
    assert (attributes[fs.FILE_ATTRIBUTE.DIRECTORY])
    assert ("directory" in attributes)
  """
  def __init__ (self, flags=0, const=FILE_ATTRIBUTE):
    self.const = const
    self.flags = flags

  def __getitem__ (self, item):
    return bool (self.flags & self.const.constant (item))
  __getattr__ = __getitem__
  __contains__ = __getitem__

  def as_string (self):
    return "%08x" % self.flags

  def dumped (self, level=0):
    return utils.dumped (
      "\n".join ("%s => %s" % (k, bool (self.flags & v)) for k, v in sorted (self.const.items ())),
      level
    )

class Drive (core._WinSysObject):
  r"""Wraps a drive letter, offering access to its :attr:`Drive.volume`
  and the ability to :meth:`mount` or :meth:`dismount` it on a particular
  volume.
  """

  def __init__ (self, drive):
    self.name = drive.lower ().rstrip (seps).rstrip (":") + ":" + sep
    self.type = wrapped (win32file.GetDriveTypeW, self.name)

  def as_string (self):
    return "Drive %s" % self.name

  def _get_root (self):
    r"""Return a :class:`fs.Dir` object corresponding to the
    root directory of this drive.
    """
    return Dir (self.name)
  root = property (_get_root)

  def _get_volume (self):
    """Any volume currently mounted on this drive root. NB A drive
    can be referred to without a volume mounted, eg to call its :meth:`mount`
    method.
    """
    try:
      return volume (self.name)
    except x_no_such_file:
      return None
  volume = property (_get_volume)

  def mount (self, vol):
    r"""Mount the specified volume in this drive.

    :param vol: anything accepted by :func:`volume`
    :returns: self
    """
    self.root ().mount (vol)
    return self

  def dismount (self):
    r"""Dismount this drive from its volume"""
    self.root ().dismount ()
    return self

  def dumped (self, level):
    output = []
    output.append ("name: %s" % self.name)
    output.append ("type (DRIVE_TYPE): %s" % DRIVE_TYPE.name_from_value (self.type))
    if self.volume:
      output.append ("volume:\n%s" % self.volume.dumped (level))
    mount_points = [(mount_point, volume) for (mount_point, volume) in mounts () if mount_point.startswith (self.name)]
    output.append ("mount_points:\n%s" % utils.dumped_list (("%s => %s" % i for i in mount_points), level))
    return utils.dumped ("\n".join (output), level)

class Volume (core._WinSysObject):
  r"""Wraps a filesystem volume, giving access to useful
  information such as the filesystem and a list of drives
  mounted on it. Also offers the ability to mount or dismount.

  Attributes:

  * :attr:`label`
  * :attr:`serial_number`
  * :attr:`maximum_component_length`
  * :attr:`flags` - combination of :const:`VOLUME_FLAG`
  * :attr:`file_system_name`
  * :attr:`mounts`
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
    """The user-assigned label set by the DOS LABEL command
    """
    return self._get_info ()[0]
  label = property (_get_label)

  def _get_serial_number (self):
    r"""A software serial number, not the hardware serial
    number assigned by the device manufacturer.
    """
    value = self._get_info ()[1]
    if value is None:
      return None
    else:
      serial_number, = struct.unpack ("L", struct.pack ("l", value))
      return serial_number
  serial_number = property (_get_serial_number)

  def _get_maximum_component_length (self):
    r"""The maximum length any one component of the file system
    name can reach. For NTFS this is 255, meaning that any one
    segment of of the path can be no longer than 255 chars.
    """
    return self._get_info ()[2]
  maximum_component_length = property (_get_maximum_component_length)

  def _get_flags (self):
    r"""An attribute set corresponding to some combination of :const:`VOLUME_FLAG`"""
    return _Attributes (self._get_info ()[3], VOLUME_FLAG)
  flags = property (_get_flags)

  def _get_file_system_name (self):
    r"""The name of the file system present on this volume, eg NTFS"""
    return self._get_info ()[4]
  file_system_name = property (_get_file_system_name)

  def _get_mounts (self):
    r"""An iterator of the :class:`Dir` objects which mount this volume. NB Windows
    restrictions mean that more than one drive root directory can mount the same
    volume simultaneously. But it is possible for a volume to be mounted on, eg,
    e:\ and c:\mounts\e at the same time.
    """
    return (dir (m) for m in wrapped (win32file.GetVolumePathNamesForVolumeName, self.name))
  mounts = property (_get_mounts)

  def change_journal (self):
    return _change_journal.ChangeJournal (self.name.rstrip ("\\"))

  def dumped (self, level):
    output = []
    output.append ("volume: %s" % self.name)
    output.append ("mounted at:\n%s" % utils.dumped_list (self.mounts, level))
    output.append ("label: %s" % self.label)
    if self.serial_number is not None:
      output.append ("serial_number: %08x" % self.serial_number)
    output.append ("maximum_component_length: %s" % self.maximum_component_length)
    output.append ("flags (VOLUME_FLAG):\n%s" % self.flags.dumped (level))
    output.append ("file_system_name: %s" % self.file_system_name)
    return utils.dumped ("\n".join (output), level)

  def mount (self, filepath):
    r"""Mount this volume on a particular filepath

    :param filepath: anything accepted by :func:`dir`
    """
    return mount (filepath, self)

  def dismount (self, filepath):
    r"""Dismount this volume from a particular filepath

    :param filepath: anything accepted by :func:`dir`
    """
    dir (filepath).dismount ()

class Entry (FilePath, core._WinSysObject):
  r"""Heart of the fs module. This is a subtype of :class:`FilePath` and
  therefore of the base str type and is the parent of the
  :class:`Dir` and :class:`File` classes and contains all the
  functionality common to both. It is rarely instantiated itself,
  altho' it's possible to do so.

  Attributes:
  * :attr:`readable`
  * :attr:`filepath`
  * :attr:`created_at`
  * :attr:`accessed_at`
  * :attr:`written_at`
  * :attr:`uncompressed_size`
  * :attr:`size`
  * :attr:`attributes`
  * :attr:`id`
  * :attr:`n_links`
  * :attr:`attributes - an :class:`_Attributes` object representing combinations of :const:`FILE_ATTRIBUTE`

  Common functionality:

  * Entries compare (eq, lt, etc.) according to their full filepath. To do a
    content-wise comparison, use :meth:`equal_contents`.
  * Entries are True according to their existence on a filesystem
  * The str representation is the filepath utf8-encoded; str is the filepath itself
  * Adding one path to another will use os.path.join semantics
  """
  def __new__ (meta, filepath, _file_info=core.UNSET):
    fp = FilePath.__new__ (meta, filepath)
    fp._normpath = normalised (fp)
    if _file_info is core.UNSET:
      fp._attributes = core.UNSET
      fp._created_at = core.UNSET
      fp._accessed_at = core.UNSET
      fp._written_at = core.UNSET
      fp._size = core.UNSET
      fp._reparse_tag = core.UNSET
    else:
      fp._attributes = _Attributes (_file_info[0])
      fp._created_at = utils.from_pytime (_file_info[1])
      fp._accessed_at = utils.from_pytime (_file_info[2])
      fp._written_at = utils.from_pytime (_file_info[3])
      fp._size = utils._longword (_file_info[5], _file_info[4])
      fp._reparse_tag = _file_info[6]
    return fp

  def as_string (self):
    return self.encode ("utf8")

  def dumped (self, level=0, show_security=False):
    output = []
    output.append (self)
    output.append (super (Entry, self).dumped (level))
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
    if self.attributes.directory:
      vol = self.mounted_by ()
      if vol:
        output.append ("Mount point for:")
        output.append (vol.dumped (level))
    if show_security:
      try:
        s = self.security ()
      except win32file.error as error:
        errno, errctx, errmsg = error
        if errno == winerror.ERROR_ACCESS_DENIED:
          pass
      else:
        output.append ("Security:\n" + s.dumped (level))
    return utils.dumped ("\n".join (output), level)

  def __add__ (self, other):
    return entry (super (Entry, self).__add__ (other))

  def __radd__ (self, other):
    return entry (super (Entry, self).__radd__ (other))

  def __bool__ (self):
    r"""Determine whether the file exists (at least from
    the POV of the current user) on the filesystem so that
    it can be checked with if fs.entry ("..."):
    """
    return (wrapped (win32file.GetFileAttributesW, self._normpath) != -1)

  @classmethod
  def factory (cls, filepath):
    return entry (filepath)

  def _get_readable (self):
    #
    # Check whether the user has at least enough
    # permissions to open the file for reading.
    #
    try:
      with Handle (self): pass
    except:
      return False
    else:
      return True
  readable = property (_get_readable)

  def get_created_at (self):
    r"""Get and store the latest creation time from the filesystem"""
    self._created_at = utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._normpath)[1])
    return self._created_at
  def _get_created_at (self):
    r"""Get the creation time from the original file read or the latest from
    the filesystem if none was stored."""
    if self._created_at is core.UNSET:
      return self.get_created_at ()
    else:
      return self._created_at
  def _set_created_at (self, created_at, handle=None):
    with Handle (handle or self.normapth, True) as handle:
      created_at = pywintypes.Time (time.mktime (created_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, created_at, None, None)
  created_at = property (_get_created_at, _set_created_at)

  def get_accessed_at (self):
    r"""Get and store the latest access time from the filesystem"""
    self._accessed_at = utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._normpath)[3])
    return self._accessed_at
  def _get_accessed_at (self):
    r"""Get the access time from the original file read or the latest from
    the filesystem if none was stored."""
    if self._accessed_at is core.UNSET:
      return self.get_accessed_at ()
    else:
      return self._accessed_at
  def _set_accessed_at (self, accessed_at, handle=None):
    with Handle (handle or self, True) as handle:
      accessed_at = pywintypes.Time (time.mktime (accessed_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, None, accessed_at, None)
  accessed_at = property (_get_accessed_at, _set_accessed_at)

  def get_written_at (self):
    r"""Get and store the latest modification time from the filesystem"""
    self._written_at = utils.from_pytime (wrapped (win32file.GetFileAttributesExW, self._normpath)[2])
    return self._written_at
  def _get_written_at (self):
    r"""Get and store the modification time from the original file read or the latest from
    the filesystem if none was stored."""
    if self._written_at is core.UNSET:
      return self.get_written_at ()
    else:
      return self._written_at
  def _set_written_at (self, written_at, handle=None):
    with Handle (handle or self, True) as handle:
      written_at = pywintypes.Time (time.mktime (written_at.timetuple ()))
      wrapped (win32file.SetFileTime, handle, None, None, written_at)
  written_at = property (_get_written_at, _set_written_at)

  def _get_uncompressed_size (self, handle=None):
    r"""Get the size of the file data, ignoring any filesystem
    compression which may have been applied.
    """
    with Handle (handle or self) as handle:
      return wrapped (win32file.GetFileSize, handle)
  uncompressed_size = property (_get_uncompressed_size)

  def get_size (self):
    r"""Get and store the latest (possibly compressed) size from the filesystem"""
    self._size = wrapped (_kernel32.GetCompressedFileSize, self._normpath)
    return self._size
  def _get_size (self):
    r"""Get and store the (possibly compressed) size from the original file read or the latest from
    the filesystem if none was stored."""
    if self._size is core.UNSET:
      return self.get_size ()
    else:
      return self._size
  size = property (_get_size)

  def get_attributes (self):
    r"""Get and store the latest file attributes from the filesystem"""
    self._attributes = _Attributes (wrapped (win32file.GetFileAttributesExW, self._normpath)[0])
    return self._attributes
  def _get_attributes (self):
    r"""Get and store the file attributes from the original file read or the latest from
    the filesystem if none was stored."""
    if self._attributes is core.UNSET:
      return self.get_attributes ()
    else:
      return self._attributes
  attributes = property (_get_attributes)

  def _get_id (self):
    r"""Return an id for this file which can be used to compare it to another while
    both files are open to determine if both are the same physical file."""
    with Handle (self) as hFile:
      file_information = wrapped (win32file.GetFileInformationByHandle, hFile)
      volume_serial_number = file_information[4]
      index_lo, index_hi = file_information[8:10]
      return volume_serial_number + (utils._longword (index_hi, index_lo) * 2 << 31)
  id = property (_get_id)

  def _get_n_links (self):
    r"""Determine how many links point to this file. >1 indicates that
    the file is hardlinked.
    """
    with Handle (self) as hFile:
      file_information = wrapped (win32file.GetFileInformationByHandle, hFile)
      return file_information[7]
  n_links = property (_get_n_links)

  def _set_file_attribute (self, key, value):
    try:
      attr = FILE_ATTRIBUTE.constant (key)
    except KeyError:
      raise AttributeError (key)
    if value:
      wrapped (win32file.SetFileAttributesW, normalised (self), self.attributes.flags | attr)
    else:
      wrapped (win32file.SetFileAttributesW, normalised (self), self.attributes.flags & ~attr)

  def _get_archive (self):
    r"Is the archive bit set on the file?"
    return self.attributes.archive
  def _set_archive (self, value):
    self._set_file_attribute ("archive", value)
  archive = property (_get_archive, _set_archive)

  def _get_compressed (self):
    r"Is the file compressed?"
    return self.attributes.compressed
  compressed = property (_get_compressed)

  def _get_directory (self):
    r"Is the file a directory?"
    return self.attributes.directory
  directory = property (_get_directory)

  def _get_encrypted (self):
    r"Is the file encrypted?"
    return self.attributes.encrypted
  encrypted = property (_get_encrypted)

  def _get_hidden (self):
    r"Is the file hidden?"
    return self.attributes.hidden
  def _set_hidden (self, value):
    self._set_file_attribute ("hidden", value)
  hidden = property (_get_hidden, _set_hidden)

  def _get_normal (self):
    r"Is the file normal?"
    return self.attributes.normal
  def _set_normal (self, value):
    wrapped (win32file.SetFileAttributesW, normalised (self), FILE_ATTRIBUTE.NORMAL)
  normal = property (_get_normal, _set_normal)

  def _get_not_content_indexed (self):
    r"Should the file's content not be indexed?"
    return self.attributes.not_content_indexed
  def _set_not_content_indexed (self, value):
    self._set_file_attribute ("not_content_indexed", value)
  not_content_indexed = property (_get_not_content_indexed, _set_not_content_indexed)

  def _get_offline (self):
    r"Is the file offline?"
    return self.attributes.offline
  def _set_offline (self, value):
    self._set_file_attribute ("offline", value)
  offline = property (_get_offline, _set_offline)

  def _get_readonly (self):
    r"Is the file readonly?"
    return self.attributes.readonly
  def _set_readonly (self, value):
    self._set_file_attribute ("readonly", value)
  readonly = property (_get_readonly, _set_readonly)

  def _get_reparse_point (self):
    r"Is the file a reparse point?"
    return self.attributes.reparse_point
  reparse_point = property (_get_reparse_point)

  def _get_sparse_file (self):
    r"Is the file sparse?"
    return self.attributes.sparse_file
  sparse_file = property (_get_sparse_file)

  def _get_system (self):
    r"Is the file a system file?"
    return self.attributes.system
  def _set_system (self, value):
    self._set_file_attribute ("system", value)
  system = property (_get_system, _set_system)

  def _get_temporary (self):
    r"Is the file a temporary file?"
    return self.attributes.temporary
  def _set_temporary (self, value):
    self._set_file_attribute ("temporary", value)
  temporary = property (_get_temporary, _set_temporary)

  def _get_virtual (self):
    r"Is the file a virtual file?"
    return self.attributes.virtual
  virtual = property (_get_virtual)

  def like (self, pattern):
    r"""Return true if this filename's name (not the path) matches
    `pattern` according to `fnmatch`, eg::

      from winsys import fs
      for f in fs.files ():
        if f.directory and f.like ("test_*"):
          print (f)

    :param pattern: an `fnmatch` pattern
    :returns: True if this file matches `pattern`
    """
    return fnmatch.fnmatch (self.name, pattern)

  def ancestors (self):
    r"""Iterate over this entry's ancestors, yielding the :class:`Dir` object
    corresponding to each one.

    :returns: yield a :class:`Dir` object for each ancestor
    """
    if self.parent:
      yield self.parent
      for ancestor in self.parent.ancestors ():
        yield ancestor

  def security (self, options=security.Security.DEFAULT_OPTIONS):
    r"""Return a :class:`security.Security` object corresponding to this
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
    :returns: a :class:`security.Security` object which may be used as a context manager
    """
    return security.security (self, options=options)

  def compress (self):
    r"""Compress this entry; if it is a file, it will be compressed, if it
    is a directory it will be marked so that any new files added to it will
    be compressed automatically.

    :returns: self
    """
    with Handle (self, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.DEFAULT)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      return self

  def uncompress (self):
    r"""Uncompress this entry; if it is a file, it will be uncompressed, if it
    is a directory it will be marked so that any new files added to it will
    not be compressed automatically.

    :returns: self
    """
    with Handle (self, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.NONE)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      return self

  def encrypt (self):
    r"""FIXME: Need to work out how to create certificates for this

    :returns: self
    """
    wrapped (win32file.EncryptFile, self._normpath)
    return self

  def unencrypt (self):
    r"""FIXME: Need to work out how to create certificates for this

    :returns: self
    """
    wrapped (win32file.DecryptFile, self._normpath)
    return self

  def encryption_users (self):
    r"""FIXME: Need to work out how to create certificates for this
    """
    return (
      (security.principal (sid), hashblob, info)
        for (sid, hashblob, info)
        in wrapped (win32file.QueryUsersOnEncryptedFile, self._normpath)
    )

  def move (self, other, callback=None, callback_data=None, clobber=False):
    r"""Move this entry to the file/directory represented by other.
    If other is a directory, self

    :param other: anything accepted by :func:`entry`
    :param callback: a function which will receive a total size & total transferred
    :param callback_data: passed as extra data to callback
    :param clobber: whether to overwrite the other file if it exists
    :returns: a :class:`File` object corresponding to the target file
    """
    other_file = entry (other)
    if other_file and other_file.directory:
      target_filepath = other_file + self.filename
    else:
      target_filepath = other_file
    flags = MOVEFILE.WRITE_THROUGH
    if clobber:
      flags |= MOVEFILE.REPLACE_EXISTING
    wrapped (
      win32file.MoveFileWithProgress,
      self._normpath,
      normalised (target_filepath),
      progress_wrapper (callback),
      callback_data,
      flags
    )
    return file (target_filepath)
  rename = move

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
  def open (self, mode="r", attributes=None, sec=None):
    r"""EXPERIMENTAL: Use the `codecs.open` function to open this file as a Python file
    object. Positional and keyword arguments are passed straight through to
    the codecs function.

    :param mode: any of the usual Python modes
    :param attributes: anything accepted by :const:`FILE_ATTRIBUTE`
    :param sec: anything accepted by :func:`Security.security`
    """
    mode = mode.lower () if mode else "r"
    self.hFile = handle (self, "r" not in mode, sec)
    flags = 0
    if "t" in mode or "b" not in mode:
      flags |= os.O_TEXT
    if "r" in mode:
      flags |= os.O_RDONLY
    elif "a" in mode or "w" in mode:
      flags |= os.O_APPEND
    self.fd = msvcrt.open_osfhandle (self.hFile, flags)
    return os.fdopen (self.fd, mode)

  def delete (self):
    r"""Delete this file

    :returns: self
    """
    wrapped (win32file.DeleteFileW, self._normpath)
    return self

  def copy (self, other, callback=None, callback_data=None):
    r"""Copy this file to another file or directory. If other is
    a directory, this file is copied into it, otherwise this file
    is copied over it.

    :param other: anything accepted by :func:`entry`
    :param callback: function receiving total size, total so far, callback_data
    :param callback_data: passed to callback
    :returns: :class:`File` object representing other
    """
    other_file = entry (other)
    if other_file and other_file.directory:
      target_filepath = other_file + self.filename
    else:
      target_filepath = other_file
    wrapped (
      win32file.CopyFileEx,
      self._normpath,
      normalised (target_filepath),
      progress_wrapper (callback),
      callback_data
    )
    return file (target_filepath)

  def equals (self, other, compare_contents=False):
    r"""Is this file equal in size, dates and attributes to another.
    if `compare_contents` is True, use filecmp to compare the contents
    of the files.

    :param other: anything accepted by :func:`file`
    :compare_contents: True to compare contents, False otherwise
    :returns: True if the files are equal in size, modification date, attributes and contents
    """
    other = entry (other)
    if self.size != other.size:
      return False
    if self.written_at != other.written_at:
      return False
    if self.attributes != other.attributes:
      return False
    if compare_contents:
      if not filecmp.cmp (f1, f2, False):
        return False
    return True

  def hard_link_to (self, other):
    r"""Create other as a hard link to this file.

    :param other: anything accepted by :func:`file`
    :returns: :class:`File` object corresponding to other
    """
    other = file (other)
    wrapped (
      win32file.CreateHardLink,
      other._normpath,
      self._normpath
    )
    return other

  def hard_link_from (self, other):
    r"""Create this file as a hard link from other

    :param other: anything accepted by :func:`file`
    :returns: this :class:`File` object
    """
    other = file (other)
    wrapped (
      win32file.CreateHardLink,
      self._normpath,
      other._normpath
    )
    return self

  def create (self, security=None):
    r"""Create this file optionally with specific security. If the
    file already exists it will not be overwritten.

    :param security: a :class:`security.Security` object
    :returns: this object
    """
    wrapped (
      win32file.CreateFile,
      self._normpath,
      FILE_ACCESS.WRITE,
      0,
      None if security is None else security.pyobject (),
      FILE_CREATION.OPEN_ALWAYS,
      0,
      None
    ).close ()
    return self

  def zip (self, zip_filename=core.UNSET, mode="w", compression=zipfile.ZIP_DEFLATED, allow_zip64=False):
    """Zip the file up into a zipfile. By default, the zipfile will have the
    name of the file with ".zip" appended and will be a sibling of the file.
    Also by default a new zipfile will be created, overwriting any existing one, and
    standard compression will be used. The filename will be stored without any directory
    information.

    A different zipfile can be specific as the zip_filename parameter, and this
    can be appended to (if it exists) by specifying "a" as the mode param.

    :param zip_filename: The name of the resulting zipfile [this file with the extension changed to .zip]
    :param mode: mode (usually "w") to pass to the zipfile constructor
    :param compression: compression level (usually DEFLATED)
    :param allow_zip64: passed to the zipfile constructor to allow > 2Gb files
    :returns: a :class:`File` object corresponding to the zipfile created
    """
    if zip_filename is core.UNSET:
      zip_filename = self.changed (ext=".zip")

    z = zipfile.ZipFile (zip_filename, mode, compression, allow_zip64)
    z.write (self, arcname=self.filename)
    z.close ()

    return file (zip_filename)

  touch = create

class Dir (Entry):

  def __new__ (meta, filepath, *args, **kwargs):
    #
    # Ensure that a directory always ends in a backslash
    #
    return Entry.__new__ (meta, filepath.rstrip (seps) + sep, *args, **kwargs)

  def is_empty (self):
    r"""Returns True if this directory is empty, False otherwise. Will fail
    if the directory does not yet exist.
    """
    for _ in self:
      return True
    else:
      return False

  def compress (self, apply_to_contents=True, callback=None):
    r"""Flag this directory so that any new files are automatically
    compressed. If apply_to_contents is True, iterate over all subdirectories
    and their files, compressing likewise.

    :param apply_to_contents: whether to compress all existing subdirectories
                              and their files
    :param callback: called for each subdirectory / file compressed
    :returns: this directory
    """
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
    r"""Flag this directory so that any new files are automatically
    not compressed. If apply_to_contents is True, iterate over all
    subdirectories and their files, uncompressing likewise.

    :param apply_to_contents: whether to uncompress all existing subdirectories
                              and their files
    :param callback: called for each subdirectory / file uncompressed
    :returns: this directory
    """
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

  def unencrypt (self, apply_to_contents=True):
    Entry.unencrypt (self)
    if apply_to_contents:
      for dirpath, dirs, files in self.walk ():
        for dir in dirs:
          dir.unencrypt (False)
        for file in files:
          file.unencrypt ()

    return self

  def disable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._normpath, True)
    return self

  def enable_encryption (self):
    wrapped (win32security.EncryptionDisable, self._normpath, False)
    return self

  def create (self, security_descriptor=None):
    r"""Create this directory, optionally specifying a security descriptor.
    If the directory already exists, silently succeed.
    All intervening directories are automatically created if they do not
    already exist. If any exists but is a file rather than a directory,
    an exception is raised.

    :param security_descriptor: anything accepted by :func:`security.security`
    :returns: a :class:`Dir` representing the newly-created directory
    """
    security_descriptor = security.security (security_descriptor)
    parts = self.parts
    root, pieces = parts[0], parts[1:]

    for i, piece in enumerate (pieces):
      path = normalised (root + sep.join (pieces[:i+1]))
      f = entry (path)
      if f:
        if not f.directory:
          raise x_fs (errctx="Dir.create", errmsg="%s exists and is not a directory" % f)
      else:
        wrapped (
          win32file.CreateDirectory,
          path,
          security_descriptor.pyobject () if security_descriptor else None
        )

    return Dir (path)

  def mkdir (self, dirname, security_descriptor=None):
    r"""Create :dirname: as a subdirectory of this directory, specifying a
    security descriptor. This is implemented in terms of :method:`create`
    by concatenating this directory and dirname and calling .create on the
    resulting :class:`Dir` object.

    :param dirname: a relative path
    :param security_descriptor: anything accepted by :func:`security.security`
    :returns: a :class:`Dir` representing the newly-created directory
    """
    return self.dir (dirname).create (security_descriptor=security_descriptor)

  def entries (self, pattern="*", *args, **kwargs):
    r"""Iterate over all entries -- files & directories -- in this directory.
    Implemented via :func:`files`

    :pattern: a |-separated list of wildcards to match
    """
    return files (self + pattern, *args, **kwargs)
  __iter__ = entries

  def file (self, name):
    r"""Return a :class:`File` object representing a file called name inside
    this directory.
    """
    return file (self + name)

  def dir (self, name):
    r"""Return a :class:`Dir` object representing a Directory called name inside
    this directory.
    """
    return dir (self + name)

  def files (self, pattern="*", *args, **kwargs):
    r"""Iterate over all files in this directory which match pattern, yielding
    a :class:`File` object for each one. Implemented via :meth:`Dir.entries`.

    :pattern: a |-separated list of wildcards to match
    """
    return (f for f in self.entries (pattern, *args, **kwargs) if isinstance (f, File))

  def dirs (self, pattern="*", *args, **kwargs):
    r"""Iterate over all directories in this directory which match pattern, yielding
    a :class:`Dir` object for each one. Implemented via :meth:`Dir.entries`.

    :pattern: a |-separated list of wildcards to match
    """
    return (f for f in self.entries (pattern, *args, **kwargs) if isinstance (f, Dir))

  def walk (self, depthfirst=False, ignore_access_errors=False):
    r"""Mimic os.walk, iterating over each directory and the files within
    in. Each iteration yields:

      :class:`Dir`, (generator for :class:`Dir` objects), (generator for :class:`File` objects)

    :param depthfirst: Whether to use breadth-first (the default) or depth-first traversal
    :param ignore_access_errors: Whether to continue traversing in the face of access-denied errors
    """
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
    r"""Iterate over this directory and all its subdirectories, yielding one
    :class:`File` object on each iteration, and optionally :class:`Dir` objects
    as well.

    :param pattern: limit the files returned by filename
    :includedirs: whether to yield directories as well as files [False]
    :depthfirst: as for :meth:`Dir.walk`
    :ignore_access_errors: as for :meth:`Dir.walk`
    """
    patterns = pattern.split ("|")
    walker = self.walk (
      depthfirst=depthfirst,
      ignore_access_errors=ignore_access_errors
    )
    for dirpath, dirs, files in walker:
      if includedirs:
        for dir in dirs:
          for pattern in patterns:
            if dir.like (pattern):
              yield dir
              break
      for file in files:
        for pattern in patterns:
          if file.like (pattern):
            yield file
            break

  def mounted_by (self):
    r"""Return the volume mounted on this directory, or None.

    :returns: a :class:`Volume` object or :const:`None`
    """
    for dir, vol in mounts ():
      if dir == self:
        return vol

  def mount (self, vol):
    r"""Mount a volume on this directory. The directory must be empty or
    an exception is raised. eg::

      from winsys import fs
      fs.dir ("c:/temp").mkdir ("c_drive").mount ("c:")

    :param vol: anything accepted by :func:`volume`
    :returns: this :class:`Dir`
    """
    for f in self.flat (includedirs=True):
      raise x_fs (errctx="Dir.mount", errmsg="You can't mount to a non-empty directory")
    vol = volume (vol)
    for m in vol.mounts:
      if not m.dirname:
        raise x_fs (errctx="Dir.mount", errmsg="Volume %s already has a drive letter %s" % (vol, m.root))

    wrapped (win32file.SetVolumeMountPoint, self, vol.name)
    return self

  def dismount (self):
    r"""Dismount whatever volume is mounted at this directory

    :returns: this :class:`Dir`
    """
    wrapped (win32file.DeleteVolumeMountPoint, self._normpath)
    return self

  def copy (self, target_filepath, callback=None, callback_data=None):
    r"""Copy this directory to another, which must be a directory if it
    exists. If it does exist, this directory's contents will be copied
    inside it; if it does not exist, this directory will become it.
    NB To copy this directory inside another, set the `target_filepath`
    to `other_directory + self.name`.

    :param target_filepath: anything accepted by :func:`entry`
    :param callback: cf :meth:`File.copy`
    :param callback_data: cf :meth:`File.copy`
    :returns: a :class:`Dir` object representing target_filepath
    """
    target = entry (target_filepath.rstrip (sep) + sep)
    if target and not target.directory:
      raise x_no_such_file (None, "Dir.copy", "%s exists but is not a directory")
    if not target:
      target.create ()

    for dirpath, dirs, files in self.walk ():
      for d in dirs:
        target_dir = Dir (target + d.relative_to (self))
        target_dir.create ()
      for f in files:
        target_file = File (target + f.relative_to (self))
        f.copy (target_file, callback, callback_data)

    return target

  def delete (self, recursive=False):
    r"""Delete this directory, optionally including its children.

    :param recursive: whether to remove all subdirectories and files first
    :returns: this :class:`Dir`
    """
    if recursive:
      for dirpath, dirs, files in self.walk (depthfirst=True):
        for d in dirs:
          d.delete (recursive=True)
        for f in files:
          f.delete ()

    wrapped (win32file.RemoveDirectory, self._normpath)
    return self

  def watch (self, *args, **kwargs):
    r"""Return a directory watcher, as per :func:`watch`
    """
    return watch (self, *args, **kwargs)

  def zip (self, zip_filename=core.UNSET, mode="w", compression=zipfile.ZIP_DEFLATED):
    """Zip the directory up into a zip file. By default, the file will have the
    name of the directory with ".zip" appended and will be a sibling of the directory.
    Also by default a new zipfile will be created, overwriting any existing one, and
    standard compression will be used. Filenames are stored as relative to this dir.

    A different zip filename can be specific as the zip_filename parameter, and this
    can be appended to (if it exists) by specifying "a" as the mode param.

    The created / appended zip file is returned.

    :param zip_filename: The name of the zip file to hold the archive of this
                         directory and its children. [directory.zip]
    :param mode: cf zipfile.ZipFile
    :param compressions: cf zipfile.ZipFile
    :returns: a :class:`File` object representing the resulting zip file
    """
    if zip_filename is core.UNSET:
      zip_filename = os.path.join (self.parent, self.name + ".zip")

    z = zipfile.ZipFile (zip_filename, mode=mode, compression=compression)
    try:
      for f in self.flat ():
        z.write (f, f.relative_to (self))
    finally:
      z.close ()

    return file (zip_filename)

  rmdir = delete

def files (pattern="*", ignore=[".", ".."], ignore_access_errors=False):
  r"""Iterate over files and directories matching pattern, which can include
  a path. Calls win32file.FindFilesIterator under the covers, which uses
  FindFirstFile / FindNextFile.

  :pattern: A string with one or more wildcard patterns, pipe-separated
  """
  for p in pattern.split ("|"):
    for f in _files (p, ignore=ignore, ignore_access_errors=ignore_access_errors):
      yield f

def _files (pattern="*", ignore=[".", ".."], ignore_access_errors=False):
  #
  # special-case ".": FindFilesIterator treats a directory
  # name as an invitation to return only that directory.
  # It treats . as an invitation to return all the files
  # in that directory
  #
  if pattern == '.':
    yield Dir (".")
    raise StopIteration

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

  parts = get_parts (str (pattern))
  dirpath = parts[0] + sep.join (parts[1:-1])
  while True:
    try:
      file_info = next (iterator)
      filename = file_info[8]
      if filename in ignore:
        continue
      filepath = os.path.join (dirpath, filename)
      yield entry (filepath, file_info)
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

def entry (filepath, _file_info=core.UNSET):
  r"""Return a :class:`File` or :class:`Dir` object representing this
  filepath.

  ======================================= ==================================================
  filepath                                Result
  ======================================= ==================================================
  :const:`None` or ""                     :const:`None`
  an :class:`Entry` or subclass object    the same object
  an existing file name                   a :class:`File` object representing that file
  an existing directory name              a :class:`Dir` object representing that directory
  a file name which doesn't exist         a :class:`Dir` if filepath ends with \\,
                                          :class:`File` otherwise
  ======================================= ==================================================
  """
  def _guess (filepath):
    r"""If the path doesn't exist on the filesystem,
    guess whether it's intended to be a dir or a file
    by looking for a trailing slash.
    """
    if filepath.endswith (sep):
      return Dir (filepath)
    else:
      return File (filepath)

  if filepath is None or filepath == "":
    return None
  elif isinstance (filepath, Entry):
    return filepath
  else:
    filepath = str (filepath)
    if _file_info is core.UNSET:
      attributes = wrapped (win32file.GetFileAttributesW, normalised (filepath))
    else:
      attributes = _file_info[0]
    if attributes == -1:
      return _guess (filepath)
    elif attributes & FILE_ATTRIBUTE.DIRECTORY:
      return Dir (filepath, _file_info)
    else:
      return File (filepath, _file_info)

def file (filepath):
  r"""Return a :class:`File` object representing this filepath on
  the filepath. If filepath is already a :class:`File` object, return
  it unchanged otherwise ensure that the filepath doesn't point to
  an existing directory and return a :class:`File` object which
  represents it.
  """
  f = entry (filepath)
  if isinstance (f, File):
    return f
  elif isinstance (f, Dir) and f:
    raise x_fs (None, "file", "%s exists but is a directory" % filepath)
  else:
    return File (filepath)

def dir (filepath):
  r"""Return a :class:`Dir` object representing this filepath on
  the filepath. If filepath is already a :class:`Dir` object, return
  it unchanged otherwise ensure that the filepath doesn't point to
  an existing file and return a :class:`Dir` object which
  represents it.
  """
  f = entry (filepath)
  if isinstance (f, Dir):
    return f
  elif isinstance (f, File) and f:
    raise x_fs (None, "dir", "%s exists but is a file" % filepath)
  else:
    return Dir (filepath)

def glob (pattern):
  r"""Mimic the built-in glob.glob functionality as a generator,
  optionally ignoring access errors.

  :param pattern: passed to :func:`files`
  :param ignore_access_errors: passed to :func:`files`
  :returns: yields a :class:`FilePath` object for each matching file
  """
  return files (pattern)

def listdir (d):
  r"""Mimic the built-in os.list functionality as a generator,
  optionally ignoring access errors.

  :param d: anything accepted by :func:`dir`
  :param ignore_access_errors: passed to :func:`files`
  :returns: yield the name of each file in directory d
  """
  return (f.name for f in files (dir (d) + "*"))

def walk (root, depthfirst=False, ignore_access_errors=False):
  r"""Walk the directory tree starting from root, optionally ignoring
  access errors.

  :param root: anything accepted by :func:`dir`
  :param depthfirst: passed to :meth:`Dir.walk`
  :param ignore_access_errors: passed to :meth:`Dir.walk`
  :returns: as :meth:`Dir.walk`
  """
  return dir (root).walk (depthfirst=depthfirst, ignore_access_errors=ignore_access_errors)

def flat (root, pattern="*", includedirs=False, depthfirst=False, ignore_access_errors=False):
  r"""Iterate over a flattened version of the directory tree starting
  from root. Implemented via :meth:`Dir.flat`.

  :param root: anything accepted by :func:`dir`
  :param pattern: passed to :meth:`Dir.flat`
  :param includedirs: passed to :meth:`Dir.flat`
  :param depthfirst: passed to :meth:`Dir.flat`
  :param ignore_access_errors: passed to :meth:`Dir.flat`
  :returns: as :meth:`Dir.flat`
  """
  return dir (root).flat (
    pattern,
    includedirs=includedirs,
    depthfirst=depthfirst,
    ignore_access_errors=ignore_access_errors
  )

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

def move (source_filepath, *args, **kwargs):
  r"""Move one :class:`Entry` object to another, implemented via :meth:`File.move` or :meth:`Dir.move`

  :param source_filepath: anything accepted by :func:`entry`
  """
  return entry (source_filepath).move (*args, **kwargs)

def copy (source_filepath, *args, **kwargs):
  r"""Copy one :class:`Entry` object to another, implemented via :meth:`File.copy` or :meth:`Dir.copy`

  :param source_filepath: anything accepted by :func:`entry`
  """
  return entry (source_filepath).copy (*args, **kwargs)

def delete (filepath):
  r"""Deletes a :class:`Entry` object, implemented via :meth:`File.delete` or :meth:`Dir.delete`

  :param filepath: anything accepted by :func:`entry`
  """
  return entry (filepath).delete ()

def rmdir (filepath, recursive=False):
  r"""Mimic the os.rmdir functionality, optionally recursing

  :param filepath: anything accepted by :func:`dir`
  :param recursive: passed to :meth:`Dir.delete`
  """
  return dir (filepath).delete (recursive=recursive)

def attributes (filepath):
  r"""Return an :class:`_Attributes` object representing the file attributes
  of filepath, implemented via :meth:`Entry.attributes`

  :param filepath: anything accepted by :func:`entry`
  :returns: an :class:`_Attributes` object
  """
  return entry (filepath).attributes

def exists (filepath):
  r"""Mimic os.path.exists, implemented via the :class:`Entry` boolean mechanism

  :param filepath: anything accepted by :func:`entry`
  :returns: :const:`True` if filepath exists, :const:`False` otherwise
  """
  return bool (entry (filepath))

def mkdir (dirpath, *args, **kwargs):
  r"""Mimic os.mkdir, implemented via :meth:`Dir.create`
  """
  return dir (dirpath).create (*args, **kwargs)

def touch (filepath):
  r"""Update a file's modification time, creating it if it
  does not exist, implemented via :meth:`File.create`

  :param filepath: anything accepted by :func:`file`
  """
  return file (filepath).create ()

def mount (filepath, vol):
  r"""Mount vol at filepath, implemented via :meth:`Dir.mount`

  :param filepath: anything accepted by :func:`dir`
  :param vol: passed to :meth:`Dir.mount`
  """
  return dir (filepath).mount (vol)

def dismount (filepath):
  r"""Dismount the volume at filepath, implemented via :meth:`Dir.dismount`

  :param filepath: anything accepted by :func:`dir`
  """
  return dir (filepath).dismount ()

def zip (filepath, *args, **kwargs):
  r"""Create and return a zip archive of filepath, implemented via :meth:`File.zip` or :meth:`Dir.zip`

  :param filepath: anything accepted by :func:`entry`
  """
  return entry (filepath).zip (*args, **kwargs)

def drive (drive):
  r"""Return a :class:`Drive` object representing drive

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
  r"""Iterate over all the drive letters in the system, yielding a :class:`Drive` object
  representing each one.
  """
  for drive in wrapped (win32api.GetLogicalDriveStrings).strip ("\x00").split ("\x00"):
    yield Drive (drive)

def volume (volume):
  r"""Return a :class:`Volume` object corresponding to volume

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
  elif volume.startswith (r"\\?\Volume"):
    return Volume (volume)
  else:
    return Volume (wrapped (win32file.GetVolumeNameForVolumeMountPoint, volume.rstrip (sep) + sep))

def volumes ():
  r"""Iterate over all the volumes in the system, yielding a :class:`Volume` object
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
  r"""Iterate over all mounted volume mountpoints in the system, yielding a
  (:class:`Dir`, :class:`Volume`) pair for each one, eg::

    from winsys import fs
    drive_volumes = dict (fs.mounts ())
  """
  for v in volumes ():
    for m in v.mounts:
      yield Dir (m), v

class _DirWatcher (object):

  WATCH_FOR = functools.reduce (operator.or_, FILE_NOTIFY_CHANGE.values ())
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

  def __next__ (self):
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
            if result != last_result:
              self._changes.append (result)

      if self._changes:
        return self._changes.popleft ()

  def stop (self):
    self.hDir.close ()

def watch (
  root,
  subdirs=False,
  watch_for=_DirWatcher.WATCH_FOR,
  buffer_size=_DirWatcher.BUFFER_SIZE
):
  r"""Return an iterator which returns a file change on every iteration.
  The file change comes in the form: action, old_filename, new_filename.
  action is one of the :const:`FILE_ACTION` constants, while the filenames
  speak for themselves. The filenames will be the same if the file has been
  updated. If the file is new, old_filename will be None; if it has been
  deleted, new_filename will be None; if it has been renamed, they will
  be different::

    from winsys import fs
    watcher = fs.watch ("c:/temp", subdirs=True)
    for action, old_filename, new_filename in watcher:
      if action == fs.FILE_ACTION.ADDED:
        print (new_filename, "added")
      elif action == fs.FILE_ACTION.REMOVED:
        print (old_filename, "removed")
  """
  return _DirWatcher (str (root), subdirs, watch_for, buffer_size)

if __name__ == '__main__':
  print ("Watching", os.path.abspath ("."))
  watcher = watch (".", True)
  try:
    for action, old_filename, new_filename in watcher:
      if action in (FILE_ACTION.ADDED, FILE_ACTION.MODIFIED):
        print ("%10s %s %d" % (FILE_ACTION.name_from_value (action), new_filename, entry (new_filename).size))
  except KeyboardInterrupt:
    watcher.stop ()
