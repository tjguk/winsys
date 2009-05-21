# -*- coding: iso-8859-1 -*-
import os, sys
from win32com import storagecon
from win32com.shell import shell, shellcon
from win32com import storagecon
import win32api
import pythoncom

from winsys import core, constants, exc

STGM = constants.Constants.from_pattern ("STGM_*", namespace=storagecon)
STGFMT = constants.Constants.from_pattern ("STGFMT_*", namespace=storagecon)
FMTID = constants.Constants.from_pattern ("FMTID_*", namespace=pythoncom)
PIDSI = constants.Constants.from_pattern ("PIDSI_*", namespace=storagecon)
PIDDSI = constants.Constants.from_pattern ("PIDDSI_*", namespace=storagecon)

PROPERTIES = {
  FMTID.SummaryInformation : PIDSI,
  FMTID.DocSummaryInformation : PIDDSI,
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
  return shell.SHGetPathFromIDList (shell.SHGetSpecialFolderLocation (0, folder_id))

def desktop (common=0):
  u"What folder is equivalent to the current desktop?"
  return get_path ((shellcon.CSIDL_DESKTOP, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)[common])

def common_desktop ():
#
# Only here because already used in code
#
  return desktop (common=1)

def application_data (common=0):
  u"What folder holds application configuration files?"
  return get_path ((shellcon.CSIDL_APPDATA, shellcon.CSIDL_COMMON_APPDATA)[common])

def favourites (common=0):
  u"What folder holds the Explorer favourites shortcuts?"
  return get_path ((shellcon.CSIDL_FAVORITES, shellcon.CSIDL_COMMON_FAVORITES)[common])
bookmarks = favourites

def start_menu (common=0):
  u"What folder holds the Start Menu shortcuts?"
  return get_path ((shellcon.CSIDL_STARTMENU, shellcon.CSIDL_COMMON_STARTMENU)[common])

def programs (common=0):
  u"What folder holds the Programs shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_PROGRAMS, shellcon.CSIDL_COMMON_PROGRAMS)[common])

def startup (common=0):
  u"What folder holds the Startup shortcuts (from the Start Menu)?"
  return get_path ((shellcon.CSIDL_STARTUP, shellcon.CSIDL_COMMON_STARTUP)[common])

def personal_folder ():
  u"What folder holds the My Documents files?"
  return get_path (shellcon.CSIDL_PERSONAL)
my_documents = personal_folder

def recent ():
  u"What folder holds the Documents shortcuts (from the Start Menu)?"
  return get_path (shellcon.CSIDL_RECENT)

def sendto ():
  u"What folder holds the SendTo shortcuts (from the Context Menu)?"
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
  source_path = source_path or u""
  if isinstance (source_path, basestring):
    source_path = os.path.abspath (source_path)
  else:
    source_path = [os.path.abspath (i) for i in source_path]
  
  target_path = target_path or ""
  if isinstance (target_path, basestring):
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
  if result <> 0:
    raise x_winshell, result
  elif n_aborted:
    raise x_winshell, u"%d operations were aborted by the user" % n_aborted

def copy_file (
  source_path, 
  target_path, 
  allow_undo=True,
  no_confirm=False,
  rename_on_collision=True,
  silent=False,
  hWnd=None
):
  u"""Perform a shell-based file copy. Copying in
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
  u"""Perform a shell-based file move. Moving in
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
  u"""Perform a shell-based file rename. Renaming in
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
  u"""Perform a shell-based file delete. Deleting in
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
  
  def __init__ (self, filepath=None):
    self._shell_link = wrapped (
      pythoncom.CoCreateInstance,
      shell.CLSID_ShellLink,
      None,
      pythoncom.CLSCTX_INPROC_SERVER,
      shell.IID_IShellLink
    )
    self.filepath = filepath
    if self.filepath:
      wrapped (
        self._shell_link.QueryInterface,
        pythoncom.IID_IPersistFile
      ).LoadFile (
        self.filepath
      )
      
  @classmethod
  def from_lnk (cls, lnk_filepath):
    return cls (lnk_filepath)
  
  @classmethod
  def from_target (cls, target_filepath):
    pass
    

def CreateShortcut (Path, Target, Arguments = "", StartIn = "", Icon = ("",0), Description = ""):
  u"""Create a Windows shortcut:

  Path - As what file should the shortcut be created?
  Target - What command should the desktop use?
  Arguments - What arguments should be supplied to the command?
  StartIn - What folder should the command start in?
  Icon - (filename, index) What icon should be used for the shortcut?
  Description - What description should the shortcut be given?

  eg
  CreateShortcut (
    Path=os.path.join (desktop (), "PythonI.lnk"),
    Target=r"c:\python\python.exe",
    Icon=(r"c:\python\python.exe", 0),
    Description="Python Interpreter"
  )
  """
  sh = pythoncom.CoCreateInstance (
    shell.CLSID_ShellLink,
    None,
    pythoncom.CLSCTX_INPROC_SERVER,
    shell.IID_IShellLink
  )

  sh.SetPath (Target)
  sh.SetDescription (Description)
  sh.SetArguments (Arguments)
  sh.SetWorkingDirectory (StartIn)
  sh.SetIconLocation (Icon[0], Icon[1])

  persist = sh.QueryInterface (pythoncom.IID_IPersistFile)
  persist.Save (Path, 1)

def property_dict (property_set_storage, fmtid):
  properties = {}
  try:
    property_storage = property_set_storage.Open (fmtid, STGM.READ | STGM.SHARE_EXCLUSIVE)
  except pythoncom.com_error, error:
    if error.strerror == 'STG_E_FILENOTFOUND':
      return {}
    else:
      raise
      
  for name, property_id, vartype in property_storage:
    if name is None:
      name = PROPERTIES.get (fmtid, constants.Constants ()).name_from_value (property_id, unicode (hex (property_id)))
    #~ if name is None:
      #~ name = hex (property_id)
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

def property_sets (filepath):
  property_set_storage = wrapped (
    pythoncom.StgOpenStorageEx,
    filepath, 
    STGM.READ | STGM.SHARE_EXCLUSIVE, 
    STGFMT.ANY, 
    0, 
    pythoncom.IID_IPropertySetStorage
  )
  for fmtid, clsid, flags, ctime, mtime, atime in property_set_storage:
    yield FMTID.name_from_value (fmtid, unicode (fmtid)), property_dict (property_set_storage, fmtid)
    if fmtid == FMTID.DocSummaryInformation:
      fmtid = pythoncom.FMTID_UserDefinedProperties
      user_defined_properties = property_dict (property_set_storage, fmtid)
      if user_defined_properties:
        yield FMTID.name_from_value (fmtid, unicode (fmtid)), user_defined_properties
