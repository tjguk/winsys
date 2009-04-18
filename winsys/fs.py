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

if not hasattr (winerror, 'ERROR_BAD_RECOVERY_POLICY'):
  winerror.ERROR_BAD_RECOVERY_POLICY = 6012

from winsys import constants, core, exc, security, utils, _kernel32
from winsys._fs.core import (
  sep, seps, 
  x_fs, x_no_such_file, x_too_many_files, x_invalid_name, x_no_certificate, x_not_ready, wrapped,
  FILE_ACCESS, FILE_SHARE, FILE_NOTIFY_CHANGE, FILE_ACTION, FILE_ATTRIBUTE,
  PROGRESS, MOVEFILE, FILE_FLAG, FILE_CREATION,
  VOLUME_FLAG, DRIVE_TYPE, COMPRESSION_FORMAT, FSCTL
)
from winsys._fs.utils import get_parts, normalised, handle, Handle
from winsys._fs.filepath import FilePath

class _Attributes (core._WinSysObject):
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

class Drive (core._WinSysObject):
  
  def __init__ (self, drive):
    if not re.match (r"[a-z](:|:/|:\\)?$", drive, re.IGNORECASE):
      raise x_fs(core.UNSET,"Drive.__init__","Invalid drive name %s"%drive)
    self.name = drive.upper().rstrip (seps).rstrip (":") + ":" + sep
    self.type = wrapped (win32file.GetDriveTypeW, self.name)
    
  def as_string (self):
    return "Drive %s" % self.name
    
  def root (self):
    return Dir (self.name)
  
  def _get_volume (self):
    try:
      return volume (self.name)
    except x_no_such_file:
      return None
  volume = property (_get_volume)
  
  def mount (self, vol):
    self.root ().mount (vol)
    return self
    
  def dismount (self):
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
    mount (filepath, self)
    
  def dismount (self, filepath):
    Dir (filepath).dismount ()
        
class Entry (core._WinSysObject):
  
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
    `pattern` according to `fnmatch`.
    """
    return fnmatch.fnmatch (self.name, pattern)
  
  def relative_to (self, other):
    ur"""Return the part of this entry's filepath which extends beyond
    other's. eg if this is 'c:/temp/abc.txt' and other is 'c:/temp/'
    then return 'abc.txt'
    """
    return self.filepath.relative_to (other)
  
  def parent (self):
    if self.filepath.parent:
      return Dir (self.filepath.parent)
    else:
      raise x_no_such_file (None, u"Entry.parent", u"%s has no parent" % self)
    
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
      return self
  
  def uncompress (self):
    with Handle (self._filepath, True) as hFile:
      compression_type = struct.pack ("H", COMPRESSION_FORMAT.NONE)
      wrapped (win32file.DeviceIoControl, hFile, FSCTL.SET_COMPRESSION, compression_type, None, None)
      return self
      
  def encrypt (self):
    wrapped (win32file.EncryptFile, self._filepath)
    return self

  def decrypt (self):
    wrapped (win32file.DecryptFile (self._filepath))
    return self
  
  def query_encryption_users (self):
    return [
      (principal (sid), hashblob, info) 
        for (sid, hashblob, info) 
        in wrapped (win32file.QueryUsersOnEncryptedFile, self._filepath)
    ]
  
  def move (self, other, callback=None, callback_data=None, clobber=False):
    ur"""Move this entry to `other`. If `other` looks like a directory
    (ie if :func:`entry` thinks it's a directory) then the target
    filepath is this file's filepath appended to `other`. If not,
    the target of the move is assumed to be the same type as this.
    
    Any directories in the target will be created as necessary.
    
    :param other: anything accepted by :func:`entry`
    :param callback: a function whose signature matches :func:`dummy_callback`
    :param callback_data: arbitrary data passed to the callback function
    :param clobber: whether to overwrite an existing entry or not [False]
    :returns: an :class:`Entry` for the target
    """
    other_file = entry (other)
    #
    # If the target is either an existing directory
    # (in which case entry will return Dir), or was
    # passed in as a Dir, assume we're copying the
    # adding the file into a directory.
    #
    if isinstance (other_file, Dir):
      target_filepath = other_file.filepath + self.filepath.filename
    else:
      target_filepath = other_file.filepath
    target_dir = dir (target_filepath.path)
    if not target_dir:
      target_dir.create ()
    
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
    return entry (target_filepath)
    
  def take_control (self, principal=core.UNSET):
    ur"""Give the logged-on user full control to a file. This may
    need to be preceded by a call to take_ownership so that the
    user gains WRITE_DAC permissions.
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
    ur"""Set the new owner of the file to be the logged-on user.
    This is no more than a slight shortcut to the equivalent
    security operations.
    
    If you specify a principal (other than the logged-in user,
    the default) you may need to have enabled SE_RESTORE privilege.
    Even the logged-in user may need to have enabled SE_TAKE_OWNERSHIP
    if that user has not been granted the appropriate security by
    the ACL.
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
    """
    deletes current file
    """
    wrapped (win32file.DeleteFileW, self._filepath)
    return self

  def copy (self, other, callback=None, callback_data=None):
    ur"""Copy this file to `other`. If `other` looks like a directory
    (ie if :func:`entry` thinks it's a directory) then the target
    filepath is this file's filepath appended to `other`. If not,
    `other` is considered to be a file and the target of the copy.
    
    Any directories in the target will be created as necessary::
    
      from winsys import fs
      source = fs.dir ("c:/temp")
      target = fs.dir ("c:/temp2")
      assert not target
      for f in source.flat ():
        if f.size > 1000000:
          f.copy (
            target.filepath + f.relative_to (source), 
            fs.dummy_callback, 
            f.filepath
          )
    
    :param other: anything accepted by :func:`entry`
    :param callback: a function whose signature matches :func:`dummy_callback`
    :param callback_data: arbitrary data passed to the callback function
    :returns: an :class:`Entry` for the target
    """
    other_file = entry (other)
    #
    # If the target is either an existing directory
    # (in which case entry will return Dir), or was
    # passed in as a Dir, assume we're copying the
    # adding the file into a directory.
    #
    if isinstance (other_file, Dir):
      target_filepath = other_file.filepath + self.filepath.filename
    else:
      target_filepath = other_file.filepath
    target_dir = dir (target_filepath.path)
    if not target_dir:
      target_dir.create ()
    wrapped (
      win32file.CopyFileEx,
      self.filepath, 
      target_filepath,
      progress_wrapper (callback), 
      callback_data
    )
    return file (target_filepath)
    
  def equal_contents (self, other):
    return self == other or filecmp.cmp (self._filepath, other.filepath)
    
  def hard_link_to (self, other):
    otherpath = normalised (unicode (other))
    wrapped (
      win32file.CreateHardLink, 
      otherpath, 
      normalised (self._filepath)
    )
    return file (normalised (unicode (other)))
    
  def hard_link_from (self, other):
    otherpath = normalised (unicode (other))
    wrapped (
      win32file.CreateHardLink, 
      normalised (self._filepath), 
      otherpath
    )
    return self

  def create (self, security=None):
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
    """Zip the file up into a zipfile. By default, the zipfile will have the
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
    target = dir (target_filepath)
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
      for dirpath, dirs, files in self.walk (depthfirst=True):
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
      zip_filename = self.filepath.changed (ext=".zip")
    
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

  def _guess (filepath):
    u"""If the path doesn't exist on the filesystem,
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
    try:
      for f in files (filepath, ignore_access_errors=ignore_access_errors):
        return f
      else:
        return _guess (filepath)
    except x_no_such_file:
      return _guess (filepath)
      
def file (filepath, ignore_access_errors=False):
  f = entry (filepath, ignore_access_errors=ignore_access_errors)
  if isinstance (f, File):
    return f
  elif isinstance (f, Dir) and f:
    raise x_fs, (None, u"file", u"%s exists but is a directory" % filepath)
  else:
    return File (filepath)

def dir (filepath, ignore_access_errors=False):
  f = entry (filepath, ignore_access_errors=ignore_access_errors)
  if isinstance (f, Dir):
    return f
  elif isinstance (f, File) and f:
    raise x_fs (None, u"dir", u"%s exists but is a file" % filepath)
  else:
    return Dir (unicode (filepath))

def glob (pattern, ignore_access_errors=False):
  dirname = os.path.dirname (pattern)
  return (entry.filepath for entry in files (pattern, ignore_access_errors=False))

def listdir (d, ignore_access_errors=False):
  pattern = dir (d).filepath + u"*"
  try:
    return (f.name for f in files (pattern, ignore_access_errors=ignore_access_errors))
  except win32file.error:
    return []

def walk (root, depthfirst=False, ignore_access_errors=False):
  for w in dir (root).walk (depthfirst, ignore_access_errors):
    yield w

def flat (root, pattern="*", includedirs=False, depthfirst=False, ignore_access_errors=False):
  for f in dir (root).flat (pattern, includedirs=includedirs, ignore_access_errors=ignore_access_errors):
    yield f

def dummy_callback (total_file_size, total_bytes_transferred, data):
  ur"""Example callback for the :func:`move` and :func:`copy` functions.
  
  :param total_file_size: total size of the file being moved/copied
  :param total_bytes_transferred: number of bytes transferred to far
  :param data: arbitrary block of data
  :returns: a True value to cancel the copy, False otherwise (including None)
  """
  if total_bytes_transferred > 0:
    print "%s: %03.2f%% so far%s\r" % (data, 1.0 * total_file_size / total_bytes_transferred, " " * 40),

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
  """
  moves file/dir from 'source_filepath' to 'target_filepath' and returns file/dir object to file/dir location
  """
  return entry (source_filepath).move (target_filepath, callback, callback_data, clobber)

def copy (source_filepath, target_filepath, callback=None, callback_data=None):
  """
  Copies file specefied in 'source_filepath' to directory specified 
  by 'target_filepath' and returns object to copied file/dir. Pass 
  the relative or full directory of target location.    
  """
  return entry (source_filepath).copy (target_filepath, callback, callback_data)

def delete (filepath):
  """
  deletes file/dir specefied by string passed into 'filepath'
  """
  return entry (filepath).delete ()
  
def rmdir (filepath, recursive=False):
  return dir (filepath).delete (recursive=recursive)

def attributes (filepath):
  return entry (filepath).attributes

def exists (filepath):
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
  return dir (dirpath).create (security)

def touch (filepath, security=None):
  return file (filepath).create (security)

def mount (filepath, vol):
  return dir (filepath).mount (vol)

def dismount (filepath):
  return dir (filepath).dismount ()

def zip (filepath, *args, **kwargs):
  return entry (filepath).zip (*args, **kwargs)

def drive (drive):
  if isinstance (drive, Drive):
    return drive
  else:
    return Drive (drive)

def drives ():
  for drive in wrapped (win32api.GetLogicalDriveStrings).strip ("\x00").split ("\x00"):
    yield Drive (drive)

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
