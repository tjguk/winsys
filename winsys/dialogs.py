import os, sys
import pythoncom
import winxpgui as win32gui
import win32api
import win32con
from win32com.shell import shell, shellcon
import struct
import uuid

from winsys.constants import *
from winsys.exceptions import *
from winsys import utils

class x_dialogs (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_dialogs)

def as_code (text):
  return text.lower ().replace (" ", "")

def _register_wndclass ():
  class_name = str (uuid.uuid1 ())
  wc = win32gui.WNDCLASS ()
  wc.SetDialogProc ()
  wc.hInstance = win32gui.dllhandle
  wc.lpszClassName = class_name
  wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
  wc.hCursor = win32gui.LoadCursor (0, win32con.IDC_ARROW)
  wc.hbrBackground = win32con.COLOR_WINDOW + 1
  wc.lpfnWndProc = {} 
  wc.cbWndExtra = win32con.DLGWINDOWEXTRA + struct.calcsize ("Pi")
  icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE

  python_exe = win32api.GetModuleHandle (None)
  wc.hIcon = win32gui.LoadIcon (python_exe, 1)
  class_atom = win32gui.RegisterClass (wc)
  return class_name
  
_class_name = _register_wndclass ()

def SendMessage (*args, **kwargs):
  return wrapped (win32gui.SendMessage, *args, **kwargs)
  
def MoveWindow (*args, **kwargs):
  return wrapped (win32gui.MoveWindow, *args, **kwargs)

class Dialog:
  """A general-purpose dialog class for collecting arbitrary information in
  text strings and handing it back to the user. Only Ok & Cancel buttons are
  allowed, and all the fields are considered to be strings. The list of
  fields is of the form: [(label, default), ...] and the values are saved
  in the same order.
  """

  IDC_LABEL_BASE = 1025
  IDC_FIELD_BASE = IDC_LABEL_BASE + 1000
  IDC_CALLBACK_BASE = IDC_FIELD_BASE + 1000

  #
  # Set up useful default gutters, general widths etc. but these
  # are mostly overridden inside the _resize routine below which
  # works on a per-dialog basis once the information and screen
  # font are known.
  #
  W = 210
  GUTTER_W = 5
  GUTTER_H = 5
  CONTROL_H = 12
  LABEL_W = 36
  FIELD_W = W - GUTTER_W - LABEL_W - GUTTER_W - GUTTER_W
  BUTTON_W = 36
  CALLBACK_W = CONTROL_H
  
  #
  # Only the standard Ok & Cancel buttons are allowed
  #
  BUTTONS = [("Cancel", win32con.IDCANCEL), ("Ok", win32con.IDOK)]

  def __init__ (self, title, fields, parent_hwnd=0):
    """Initialise the dialog with a title and a list of fields of
    the form [(label, default), ...].
    """
    wrapped (win32gui.InitCommonControls)
    self.hinst = win32gui.dllhandle
    self.title = title
    self.fields = list (fields)
    if not self.fields:
      raise RuntimeError ("Must pass at least one field")
    self.parent_hwnd = parent_hwnd
    self.results = []
    
  def _get_dialog_template (self, dlg_class_name):
    """Put together a sensible default layout for this dialog, taking
    into account the default structure and the (variable) number of fields.
    
    NB Although sensible default positions are chosen here, the horizontal
    layout will be overridden by the _resize functionality below.
    """
    style = win32con.WS_THICKFRAME | win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.DS_SETFONT | win32con.WS_MINIMIZEBOX
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE

    dlg_h = self.GUTTER_H + len (self.fields) * (self.CONTROL_H + self.GUTTER_H) + self.CONTROL_H + self.GUTTER_H
    dlg = [[self.title, (0, 0, self.W, dlg_h), style, None, (9, "Lucida Sans Regular"), None, dlg_class_name],]

    for i, (field, default_value, callback) in enumerate (self.fields):
      label_l = self.GUTTER_W
      label_t = self.GUTTER_H + (self.CONTROL_H + self.GUTTER_H) * i
      field_l = label_l + self.LABEL_W + self.GUTTER_W
      field_t = label_t
      field_h = self.CONTROL_H

      dlg.append (["STATIC", field, self.IDC_LABEL_BASE + i, (label_l, label_t, self.LABEL_W, self.CONTROL_H), cs | win32con.SS_LEFT])
      if (default_value is True or default_value is False):
        field_type = "BUTTON"
        field_styles = win32con.WS_TABSTOP | win32con.BS_AUTOCHECKBOX
        field_w = self.CONTROL_H
      elif isinstance (default_value, list):
        if callback is not None:
          raise RuntimeError ("Cannot combine a list with a callback")
        field_type = "COMBOBOX"
        field_styles = win32con.WS_TABSTOP | win32con.CBS_DROPDOWNLIST
        field_w = self.FIELD_W
        field_h = 4 * self.CONTROL_H
      else:
        field_type = "EDIT"
        field_styles = win32con.WS_TABSTOP | win32con.WS_BORDER
        field_w = self.FIELD_W - ((self.CALLBACK_W) if callback else 0)
        
      dlg.append ([field_type, None, self.IDC_FIELD_BASE + i, (field_l, field_t, field_w, field_h), cs | field_styles])
      if callback:
        dlg.append (["BUTTON", "...", self.IDC_CALLBACK_BASE + i, (field_l + field_w + self.GUTTER_W, field_t, self.CALLBACK_W, self.CONTROL_H), cs | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON])

    cs = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON
    button_t = field_t + self.CONTROL_H + self.GUTTER_H
    for i, (caption, id) in enumerate (reversed (self.BUTTONS)):
      dlg.append (["BUTTON", caption, id, (self.W - ((i + 1) * (self.GUTTER_W + self.BUTTON_W)), button_t, self.BUTTON_W, self.CONTROL_H), cs])

    return dlg

  def run (self):
    """The heart of the dialog box functionality. The call to DialogBoxIndirect
    kicks off the dialog's message loop, finally returning via the EndDialog call
    in OnCommand
    """
    message_map = {
      win32con.WM_COMMAND: self.OnCommand,
      win32con.WM_INITDIALOG: self.OnInitDialog,
      win32con.WM_SIZE: self.OnSize,
      win32con.WM_GETMINMAXINFO : self.OnMinMaxInfo,
    }
    return wrapped (
      win32gui.DialogBoxIndirect,
      self.hinst, 
      self._get_dialog_template (_register_wndclass ()), 
      self.parent_hwnd,
      message_map
    )

  def OnInitDialog (self, hwnd, msg, wparam, lparam):
    """Attempt to position the dialog box more or less in
    the middle of its parent (possibly the desktop). Then
    force a resize of the dialog controls which should take
    into account the different label lengths and the dialog's
    new size.
    """
    self.hwnd = hwnd
    for i, (field, default, callback) in enumerate (self.fields):
      self._set_item (self.IDC_FIELD_BASE + i, default)

    parent = self.parent_hwnd or wrapped (win32gui.GetDesktopWindow)
    l, t, r, b = wrapped (win32gui.GetWindowRect, self.hwnd)
    dt_l, dt_t, dt_r, dt_b = wrapped (win32gui.GetWindowRect, parent)
    centre_x, centre_y = wrapped (win32gui.ClientToScreen, parent, ((dt_r - dt_l) / 2, (dt_b - dt_t) / 2))
    wrapped (win32gui.MoveWindow, self.hwnd, centre_x - (r / 2), centre_y - (b / 2), r - l, b - t, 0)
    l, t, r, b = wrapped (win32gui.GetClientRect, self.hwnd)
    self._resize (r - l, b - t, 0)
    return True

  def _resize (self, dialog_w, dialog_h, repaint=1):
    """Attempt to resize the controls on the dialog, spreading
    then horizontally to cover the full extent of the dialog
    box, with left-aligned labels and right-aligned buttons.
    """
    
    def coords (hwnd, id):
      ctrl = wrapped (win32gui.GetDlgItem, hwnd, id)
      l, t, r, b = wrapped (win32gui.GetWindowRect, ctrl)
      l, t = wrapped (win32gui.ScreenToClient, hwnd, (l, t))
      r, b = wrapped (win32gui.ScreenToClient, hwnd, (r, b))
      return ctrl, l, t, r, b
    
    hDC = wrapped (win32gui.GetDC, self.hwnd)
    label_w, label_h = max (wrapped (win32gui.GetTextExtentPoint32, hDC, label) for label, _, _ in self.fields)
    wrapped (win32gui.ReleaseDC, self.hwnd, hDC)
    
    for i, (field, default, callback) in enumerate (self.fields):
      label, l, t, r, b = coords (self.hwnd, self.IDC_LABEL_BASE + i)
      wrapped (win32gui.MoveWindow, label, self.GUTTER_W, t, label_w, b - t, repaint)
      label_r = self.GUTTER_W + label_w
      
      if callback:
        callback_button, l, t, r, b = coords (self.hwnd, self.IDC_CALLBACK_BASE + i)
        callback_w = r - l
        callback_l = dialog_w - self.GUTTER_W - callback_w
        wrapped (win32gui.MoveWindow, callback_button, callback_l, t, r - l, b - t, repaint)
      else:
        callback_w = 0
      
      field, l, t, r, b = coords (self.hwnd, self.IDC_FIELD_BASE + i)
      field_l = label_r + self.GUTTER_W
      field_w = dialog_w - self.GUTTER_W - field_l - (callback_w + self.GUTTER_W if callback_w else 0)
      wrapped (win32gui.MoveWindow, field, field_l, t, field_w, b - t, repaint)

    for i, (caption, id) in enumerate (reversed (self.BUTTONS)):
      button, l, t, r, b = coords (self.hwnd, id)
      wrapped (win32gui.MoveWindow, button, dialog_w - ((i + 1) * (self.GUTTER_W + (r - l))), t, r - l, b - t, repaint)

  def _get_item (self, item_id):
    hwnd = win32gui.GetDlgItem (self.hwnd, item_id)
    class_name = win32gui.GetClassName (hwnd)
    if class_name == "Edit":      
      try:
        #
        # There is a bug/feature which prevents empty dialog items
        # from having their text read. Assume any error means that
        # the control is empty.
        #
        return win32gui.GetDlgItemText (self.hwnd, item_id)
      except:
        return ""
    elif class_name == "Button":
      return bool (win32gui.SendMessage (hwnd, win32con.BM_GETCHECK, 0, 0))
    elif class_name == "ComboBox":
      field, default, callback = self.fields[item_id - self.IDC_FIELD_BASE]
      return default[win32gui.SendMessage (hwnd, win32con.CB_GETCURSEL, 0, 0)]
    else:
      raise RuntimeError ("Unknown class: %s" % class_name)
      
  def _set_item (self, item_id, value):
    item_hwnd = win32gui.GetDlgItem (self.hwnd, item_id)
    class_name = win32gui.GetClassName (item_hwnd)
    if class_name == "Edit":
      win32gui.SetDlgItemText (self.hwnd, item_id, str (value))
    elif class_name == "Button":
      win32gui.SendMessage (item_hwnd, win32con.BM_SETCHECK, int (value), 0)
    elif class_name == "ComboBox":
      for item in value:
        win32gui.SendMessage (item_hwnd, win32con.CB_ADDSTRING, 0, utils.string_as_pointer (str (item)))
      win32gui.SendMessage (item_hwnd, win32con.CB_SETCURSEL, 0, 0)
    else:
      raise RuntimeError ("Unknown class: %s" % class_name)
  
  def OnSize (self, hwnd, msg, wparam, lparam):
    """If the dialog box is resized, force a corresponding resize
    of the controls
    """
    w = win32api.LOWORD (lparam)
    h = win32api.HIWORD (lparam)
    self._resize (w, h)
    return 0
    
  def OnMinMaxInfo (self, hwnd, msg, wparam, lparam):
    """Prevent the dialog from resizing vertically by extracting
    the window's current size and using the minmaxinfo message
    to set the maximum window height to be its current height.
    """
    dlg_l, dlg_t, dlg_r, dlg_b = win32gui.GetWindowRect (hwnd)
    #
    # MINMAXINFO is a struct of 5 POINT items, each of which
    # is a pair of LONGs. We extract the structure into a list,
    # set it's final item (the Y coord of MaxTrackSize) to be
    # the window's current height and write the data back into
    # the same place.
    #
    POINT_FORMAT = "LL"
    MINMAXINO_FORMAT = 5 * POINT_FORMAT
    data = win32gui.PyGetString (lparam, struct.calcsize (MINMAXINO_FORMAT))
    minmaxinfo = list (struct.unpack (MINMAXINO_FORMAT, data))
    minmaxinfo[9] = dlg_b - dlg_t
    win32gui.PySetMemory (lparam, struct.pack (MINMAXINO_FORMAT, *minmaxinfo))
    return 0

  def OnCommand (self, hwnd, msg, wparam, lparam):
    """React to commands from the dialog controls, principally
    the buttons. If Ok is pressed, set the ok_pressed flag and
    store the results. If cancel, reset the ok_pressed flag and
    clear results. In either case, end the dialog.
    """
    id = win32api.LOWORD (wparam)
    #
    # If OK is pressed, copy the fields' current values
    # into a list in the order in which they were passed
    # in and displayed and then exit. If Cancel is pressed,
    # exit without copying the values, resulting in an
    # empty list.
    #
    if id == win32con.IDOK:
      self.results = [self._get_item (self.IDC_FIELD_BASE + i) for i, field in enumerate (self.fields)]
      win32gui.EndDialog (self.hwnd, win32con.IDOK)
    elif id == win32con.IDCANCEL:
      self.results = []
      win32gui.EndDialog (self.hwnd, win32con.IDCANCEL)
    
    #
    # If one of the callback buttons is pressed, call the
    # corresponding callback function, passing the dialog's
    # hwnd and the field's current value. (This is to
    # facilitate things like a further dialog to fetch
    # a filename).
    #
    elif self.IDC_CALLBACK_BASE <= id < (self.IDC_CALLBACK_BASE + len (self.fields)):
      field_id = self.IDC_FIELD_BASE + id - self.IDC_CALLBACK_BASE
      field, default, callback = self.fields[field_id - self.IDC_FIELD_BASE]
      result = callback (self.hwnd, self._get_item (field_id))
      if result:
        self._set_item (field_id, result)

def dialog (title, *fields):
  """Shortcut function to populate and run a dialog, returning
  the button pressed and values saved.
  """
  _fields = []
  for field in fields:
    if len (field) < 3:
      _fields.append (tuple (field) + (None,))
    else:
      _fields.append (tuple (field))
  d = Dialog (title, _fields)
  d.run ()
  return d.results

def get_filename (start_folder=None, hwnd=None):
  """Quick interface to the shell's browse-for-folder dialog,
  optionally starting in a particular folder and allowing file
  and share selection.
  """
  def _set_start_folder (hwnd, msg, lp, data):
    if msg == BFFM.INITIALIZED and data:
      win32gui.SendMessage (hwnd, BFFM.SETSELECTION, 1, utils.string_as_pointer (data))
  
  pythoncom.CoInitialize ()
  try:
    pidl, display_name, image_list = shell.SHBrowseForFolder (
      hwnd or win32gui.GetDesktopWindow (),
      None,
      "Select a file or folder",
      BIF.BROWSEINCLUDEFILES | BIF.USENEWUI | BIF.SHAREABLE,
      _set_start_folder,
      start_folder
    )
  finally:
    pythoncom.CoUninitialize ()

  if (pidl, display_name, image_list) == (None, None, None):
    return None
  else:
    return shell.SHGetPathFromIDList (pidl)

if __name__=='__main__':
  def _get_filename (hwnd, data): 
    return get_filename (data, hwnd)
  print dialog (
    "Test", 
    ('Root', r'\\vogbs022\user', _get_filename), 
    ('Ignore access errors', True), 
    ('Size Threshold (Mb)', '100')
  )  
  print dialog ("Test2", ("Scan from:", r"c:\temp", _get_filename), ("List of things", ['Timothy', 'John', 'Golden']))
