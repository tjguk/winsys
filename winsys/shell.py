# -*- coding: iso-8859-1 -*-
r"""Wrappers around standard functionality from the semi-independent Windows Shell
subsystem which powers the desktop, shortcuts, special folders, property sheets &c.

Implemented so far:

* Shortcuts: use the :func:`shortcut` function to edit or create desktop shortcuts
* [EXPERIMENTAL] Properties: use the :func:`properties` function to expose property sheet data
* Standard folders: commonly-accessed shell folders are exposed at module level, eg :func:`desktop`,
  :func:`startup`, :func:`recent`
"""
import os, sys
import binascii

from win32com import storagecon
from win32com.shell import shell, shellcon
from win32com import storagecon
import win32api
import pythoncom
import pywintypes

from winsys import core, constants, exc, fs, utils

CSIDL = constants.Constants.from_pattern ("CSIDL_*", namespace=shellcon)
STGM = constants.Constants.from_pattern ("STGM_*", namespace=storagecon)
STGFMT = constants.Constants.from_pattern ("STGFMT_*", namespace=storagecon)
FMTID = constants.Constants.from_pattern ("FMTID_*", namespace=pythoncom)
FMTID.update (constants.Constants.from_pattern ("FMTID_*", namespace=shell))
PIDSI = constants.Constants.from_pattern ("PIDSI_*", namespace=storagecon)
PIDDSI = constants.Constants.from_pattern ("PIDDSI_*", namespace=storagecon)
PIDMSI = constants.Constants.from_pattern ("PIDMSI_*", namespace=shellcon)
PIDASI = constants.Constants.from_pattern ("PIDASI_*", namespace=shellcon)
PID_VOLUME = constants.Constants.from_pattern ("PID_VOLUME_*", namespace=shellcon)
SHCONTF = constants.Constants.from_pattern ("SHCONTF_*", namespace=shellcon)
SHGDN = constants.Constants.from_pattern ("SHGDN_*", namespace=shellcon)
SLGP = constants.Constants.from_pattern ("SLGP_*", namespace=shell)

PROPERTIES = {
  FMTID.SummaryInformation : PIDSI,
  FMTID.DocSummaryInformation : PIDDSI,
  FMTID.MediaFileSummaryInformation : PIDMSI,
  FMTID.AudioSummaryInformation : PIDASI,
  FMTID.Volume : PID_VOLUME,
}

class x_shell (exc.x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_shell)

#
# Although this can be done in one call, Win9x didn't
#  support it, so I added this workaround.
#
def get_path (folder_id):
  return fs.dir (shell.SHGetPathFromIDList (shell.SHGetSpecialFolderLocation (0, folder_id)))

def desktop (common=0):
  "What folder is equivalent to the current desktop?"
  return get_path ((shellcon.CSIDL_DESKTOP, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)[common])

def special_folder (folder_id):
  return shell.SHGetSpecialFolderPath (None, CSIDL.constant (folder_id), 0)

def application_data (common=0):
  "What folder holds application configuration files?"
  return get_path ((shellcon.CSIDL_APPDATA, shellcon.CSIDL_COMMON_APPDATA)[common])

def favourites (common=0):
  "What folder holds the Explorer favourites shortcuts?"
  return get_path ((shellcon.CSIDL_FAVORITES, shellcon.CSIDL_COMMON_FAVORITES)[common])
bookmarks = favourites

def start_menu (common=0):
  "What folder holds the Start Menu shortcuts?"
  return get_path ((shellcon.CSIDL_STARTMENU, shellcon.CSIDL_COMMON_STARTMENU)[common])

def programs (common=0):
  "What folder holds the Programs shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_PROGRAMS, shellcon.CSIDL_COMMON_PROGRAMS)[common])

def startup (common=0):
  "What folder holds the Startup shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_STARTUP, shellcon.CSIDL_COMMON_STARTUP)[common])

def personal_folder ():
  "What folder holds the My Documents files?"
  return get_path (shellcon.CSIDL_PERSONAL)
my_documents = personal_folder

def recent ():
  "What folder holds the Documents shortcuts (from the Start Menu)?"
  return get_path (shellcon.CSIDL_RECENT)

def sendto ():
  "What folder holds the SendTo shortcuts (from the Context Menu)?"
  return get_path (shellcon.CSIDL_SENDTO)

#
# Internally abstracted function to handle one
#  of several shell-based file manipulation
#  routines. Not all the possible parameters
#  are covered which might be passed to the
#  underlying SHFileOperation API call, but
#  only those which seemed useful to me at
#  the time.
#
def _file_operation (
  operation,
  source_path,
  target_path=None,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  #
  # At present the Python wrapper around SHFileOperation doesn't
  # allow lists of files. Hopefully it will at some point, so
  # take account of it here.
  # If you pass this shell function a "/"-separated path with
  # a wildcard, eg c:/temp/*.tmp, it gets confused. It's ok
  # with a backslash, so convert here.
  #
  source_path = source_path or ""
  if isinstance (source_path, str):
    source_path = os.path.abspath (source_path)
  else:
    source_path = [os.path.abspath (i) for i in source_path]

  target_path = target_path or ""
  if isinstance (target_path, str):
    target_path = os.path.abspath (target_path)
  else:
    target_path = [os.path.abspath (i) for i in target_path]

  flags = 0
  if allow_undo: flags |= shellcon.FOF_ALLOWUNDO
  if no_confirm: flags |= shellcon.FOF_NOCONFIRMATION
  if rename_on_collision: flags |= shellcon.FOF_RENAMEONCOLLISION
  if silent: flags |= shellcon.FOF_SILENT

  result, n_aborted = shell.SHFileOperation (
    (hWnd or 0, operation, source_path, target_path, flags, None, None)
  )
  if result != 0:
    raise x_winshell (result)
  elif n_aborted:
    raise x_winshell ("%d operations were aborted by the user" % n_aborted)

def copy_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file copy. Copying in
   this way allows the possibility of undo, auto-renaming,
   and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
   clobber on a name clash, automatically rename on collision
   and display the animation.
  """
  _file_operation (
    shellcon.FO_COPY,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def move_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file move. Moving in
   this way allows the possibility of undo, auto-renaming,
   and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
   clobber on a name clash, automatically rename on collision
   and display the animation.
  """
  _file_operation (
    shellcon.FO_MOVE,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def rename_file (
  source_path,
  target_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file rename. Renaming in
   this way allows the possibility of undo, auto-renaming,
   and showing the "flying file" animation during the copy.

  The default options allow for undo, don't automatically
   clobber on a name clash, automatically rename on collision
   and display the animation.
  """
  _file_operation (
    shellcon.FO_RENAME,
    source_path,
    target_path,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

def delete_file (
  source_path,
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  """Perform a shell-based file delete. Deleting in
   this way uses the system recycle bin, allows the
   possibility of undo, and showing the "flying file"
   animation during the delete.

  The default options allow for undo, don't automatically
   clobber on a name clash, automatically rename on collision
   and display the animation.
  """
  _file_operation (
    shellcon.FO_DELETE,
    source_path,
    None,
    allow_undo,
    no_confirm,
    rename_on_collision,
    silent,
    hWnd
  )

class Shortcut (core._WinSysObject):

  def __init__ (self, filepath=core.UNSET, **kwargs):
    self._shell_link = wrapped (
      pythoncom.CoCreateInstance,
      shell.CLSID_ShellLink,
      None,
      pythoncom.CLSCTX_INPROC_SERVER,
      shell.IID_IShellLink
    )
    self.filepath = filepath
    if self.filepath and os.path.exists (self.filepath):
      wrapped (
        self._shell_link.QueryInterface,
        pythoncom.IID_IPersistFile
      ).Load (
        self.filepath
      )
    for k, v in kwargs.items ():
      setattr (self, k, v)

  def as_string (self):
    return ("-> %s" % self.path) or "-unsaved-"

  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append ("")
    for attribute in ["arguments", "description", "hotkey", "icon_location", "path", "show_cmd", "working_directory"]:
      output.append ("%s: %s" % (attribute, getattr (self, attribute)))
    return utils.dumped ("\n".join (output), level)

  @classmethod
  def from_lnk (cls, lnk_filepath):
    return cls (lnk_filepath)

  @classmethod
  def from_target (cls, target_filepath, lnk_filepath=core.UNSET, **kwargs):
    target_filepath = os.path.abspath (target_filepath)
    if lnk_filepath is core.UNSET:
      lnk_filepath = os.path.join (os.getcwd (), os.path.basename (target_filepath) + ".lnk")
    return cls (
      lnk_filepath,
      path=target_filepath,
      **kwargs
    )

  def __enter__ (self):
    return self

  def __exit__ (self, exc_type, exc_val, exc_tb):
    if exc_type is None:
      self.write ()

  def _get_arguments (self):
    return self._shell_link.GetArguments ()
  def _set_arguments (self, arguments):
    self._shell_link.SetArguments (arguments)
  arguments = property (_get_arguments, _set_arguments)

  def _get_description (self):
    return self._shell_link.GetDescription ()
  def _set_description (self, description):
    self._shell_link.SetDescription (description)
  description = property (_get_description, _set_description)

  def _get_hotkey (self):
    return self._shell_link.GetHotkey ()
  def _set_hotkey (self, hotkey):
    self._shell_link.SetHotkey (hotkey)
  hotkey = property (_get_hotkey, _set_hotkey)

  def _get_icon_location (self):
    path, index = self._shell_link.GetIconLocation ()
    return fs.entry (path), index
  def _set_icon_location (self, icon_location):
    self._shell_link.SetIconLocation (*icon_location)
  icon_location = property (_get_icon_location, _set_icon_location)

  def _get_path (self):
    filepath, data = self._shell_link.GetPath (SLGP.UNCPRIORITY)
    return fs.entry (filepath)
  def _set_path (self, path):
    self._shell_link.SetPath (path)
  path = property (_get_path, _set_path)

  def _get_show_cmd (self):
    return self._shell_link.GetShowCmd ()
  def _set_show_cmd (self, show_cmd):
    self._shell_link.SetShowCmd (show_cmd)
  show_cmd = property (_get_show_cmd, _set_show_cmd)

  def _get_working_directory (self):
    return fs.dir (self._shell_link.GetWorkingDirectory ())
  def _set_working_directory (self, working_directory):
    self._shell_link.SetWorkingDirectory (working_directory)
  working_directory = property (_get_working_directory, _set_working_directory)

  def write (self, filepath=core.UNSET):
    if not filepath:
      filepath = self.filepath
    if filepath is None:
      raise x_shell (errmsg="Must specify a filepath for an unsaved shortcut")

    wrapped (
        self._shell_link.QueryInterface,
        pythoncom.IID_IPersistFile
      ).Save (
        self.filepath,
        filepath == self.filepath
      )

    self.filepath = filepath
    return self

def shortcut (source=core.UNSET):
  if source is None:
    return None
  elif source is core.UNSET:
    return Shortcut ()
  elif isinstance (source, Shortcut):
    return source
  elif source.endswith (".lnk"):
    return Shortcut.from_lnk (source)
  else:
    return Shortcut.from_target (source)

class PropertySet (core._WinSysObject):

  def __init__ (self, property_set_storage, fmtid):
    self.property_set_storage = property_set_storage
    self.fmtid = fmtid

  def as_string (self):
    return FMTID.name_from_value (self.fmtid)

  def as_dict (self):
    try:
      property_storage = self.property_set_storage.Open (self.fmtid, STGM.READ | STGM.SHARE_EXCLUSIVE)
    except pythoncom.com_error as error:
      if error.strerror == 'STG_E_FILENOTFOUND':
        return {}
      else:
        raise

    properties = {}
    for name, property_id, vartype in property_storage:
      if name is None:
        property_names = PROPERTIES.get (self.fmtid, constants.Constants ())
        name = property_names.name_from_value (property_id, str (hex (property_id)))
      try:
        for value in property_storage.ReadMultiple ([property_id]):
          properties[name] = value
      #
      # There are certain values we can't read; they
      # raise type errors from within the pythoncom
      # implementation, thumbnail
      #
      except TypeError:
        properties[name] = None
    return properties

  def __getattr__ (self, attr):
    return self.as_dict ()[attr]

  def keys (self):
    return self.as_dict ().keys ()

  def values (self):
    return self.as_dict ().values ()

  def items (self):
    return self.as_dict ().items ()

class Properties (core._WinSysObject):

  def __init__ (self, filepath):
    self._pidl, _ = shell.SHILCreateFromPath (os.path.abspath (filepath), 0)
    self._pss = shell.SHGetDesktopFolder ().BindToStorage (self._pidl, None, pythoncom.IID_IPropertySetStorage)

  def property_set (self, fmtid):
    return PropertySet (self._pss, FMTID.constant (fmtid))
  __getattr__ = property_set
  __getitem__ = property_set

  def __iter__ (self):
    for fmtid, clsid, flags, ctime, mtime, atime in self._pss:
      yield self.property_set (fmtid)
      if fmtid == FMTID.DocSummaryInformation:
        fmtid = pythoncom.FMTID_UserDefinedProperties
        yield self.property_set (fmtid)

  def dumped (self, level=0):
    output = []
    for ps in self:
      output.append ("%s:\n%s" % (FMTID.name_from_value (ps.fmtid), utils.dumped_dict (ps.as_dict (), level)))
    return utils.dumped ("\n".join (output), level)

def properties (source):

  if source is None:
    return None
  elif isinstance (source, Properties):
    return source
  else:
    return Properties (source)

_desktop = shell.SHGetDesktopFolder ()
PyIShellFolder = type (_desktop)
PyIID = type (pywintypes.IID ("{00000000-0000-0000-0000-000000000000}"))

class ShellEntry (core._WinSysObject):

  def __init__ (self, rpidl, parent=core.UNSET):
    self.parent = _desktop if parent is core.UNSET else parent
    self.rpidl = rpidl

  def as_string (self):
    return self.parent.GetDisplayNameOf (self.rpidl, SHGDN.NORMAL)

class ShellItem (ShellEntry):
  pass

class ShellFolder (ShellEntry):

  #~ def __getattr__ (self, attr):
    #~ return getattr (self.shell_folder, attr)

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


  def walk (self, depthfirst=False):
    top = self.shell_folder
    folders = [shell_folder (f, self.shell_folder) for f in self.shell_folder.EnumObjects (None, SHCONTF.FOLDERS)]
    non_folders = [self.shell_folder.EnumObjects (None, SHCONTF.NONFOLDERS)]
    if not depthfirst:
        yield top,

    for pidl in self.shell_folder:
      yield self.shell_folder.GetDisplayNameOf (pidl, 0)
      try:
        for i in shell_folder (self.shell_folder.BindToObject (pidl, None, shell.IID_IShellFolder)).walk ():
          yield i
      except shell.error:
        pass

def shell_entry (shell_entry=core.UNSET):
  if shell_entry is None:
    return None
  elif shell_entry is core.UNSET:
    return ShellFolder ([], _desktop)
  elif isinstance (ShellEntry, shell_entry):
    return shell_entry
  elif isinstance (shell_entry, str):
    pidl, flags = shell.SHILCreateFromPath (os.path.abspath (shell_folder), SHCONTF.FOLDERS)
    if pidl is None:
      return ShellFolder (
        shell.SHGetFolderLocation (None, CSIDL.constant (shell_entry), None, 0),
        _desktop
      )
      pidl = None
    return ShellFolder (_desktop.BindToObject (pidl, None, shell.IID_IShellFolder))


def shell_folder (shell_folder=core.UNSET, parent=core.UNSET):
  if shell_folder is None:
    return None
  elif shell_folder is core.UNSET:
    return ShellFolder ([], _desktop)
  elif isinstance (shell_folder, PyIShellFolder):
    return ShellFolder (shell_folder)
  elif isinstance (shell_folder, str):
    pidl, flags = shell.SHILCreateFromPath (os.path.abspath (shell_folder), 0)
    if pidl is None:
      pidl = shell.SHGetFolderLocation (None, CSIDL.constant (shell_folder), None, 0)
    return ShellFolder (_desktop.BindToObject (pidl, None, shell.IID_IShellFolder))
  elif isinstance (shell_folder, list):
    if parent is core.UNSET:
      raise x_shell (errctx="shell_folder", errmsg="Cannot bind to PIDL without parent")
    return ShellFolder (parent.BindToObject (shell_folder, None, shell.IID_IShellFolder))
  else:
    raise x_shell (errctx="shell_folder")
