r"""Provides for simple dialog boxes, doing just enough to return input
from the user using edit controls, dropdown lists and checkboxes. Most
interaction is via the :func:`dialog`, :func:`progress_dialog` or
:func:`info_dialog` functions. This example offers the user a drop-down
list of installed Python directories, a text box to enter a size threshold and a
checkbox to indicate whether to email the result::

  from winsys import dialogs, registry
  SIZE_THRESHOLD_MB = "100"
  PYTHONREG = registry.registry (r"hklm\software\python\pythoncore")
  version, size_threshold_mb, email_result = dialogs.dialog (
    "Find big files in Python",
    ("Version", [k.InstallPath.get_value ("") for k in PYTHONREG.keys ()]),
    ("Bigger than (Mb)", SIZE_THRESHOLD_MB),
    ("Email?", False)
  )

All dialogs are resizable horizontally but not vertically. All
edit boxes (fields with a default which is a string) accept file-drops,
eg from Explorer.

The standard dialog (from :func:`dialog`) is modal and returns a tuple
of values as soon as [Ok] is pressed or an empty list if [Cancel] is pressed.
The progress dialog (from :func:`progress_dialog`) is also modal, but
passes the tuple of values to a callback which yields update strings which
are then displayed in the status box on the dialog. When the callback
function completes, the dialog returns the tuple of values to the caller.
:func:`info_dialog` is intended to be used for, eg, displaying a
traceback or other bulky text for which a message box might be awkward.
It displays multiline text in a readonly edit control which can be
scrolled and select-copied.
"""
import os, sys
import datetime
import functools
import marshal
import operator

import pythoncom
import winxpgui as win32gui
import pythoncom
import win32com.server.policy
import win32api
import win32con
import win32cred
import win32event
from win32com.shell import shell, shellcon
import win32ui
import struct
import threading
import traceback
import uuid

from winsys import core, constants, exc, utils

BIF = constants.Constants.from_dict (dict (
  BIF_RETURNONLYFSDIRS   = 0x0001,
  BIF_DONTGOBELOWDOMAIN  = 0x0002,
  BIF_STATUSTEXT         = 0x0004,
  BIF_RETURNFSANCESTORS  = 0x0008,
  BIF_EDITBOX            = 0x0010,
  BIF_VALIDATE           = 0x0020,
  BIF_NEWDIALOGSTYLE     = 0x0040,
  BIF_BROWSEINCLUDEURLS  = 0x0080,
  BIF_UAHINT             = 0x0100,
  BIF_NONEWFOLDERBUTTON  = 0x0200,
  BIF_NOTRANSLATETARGETS = 0x0400,
  BIF_BROWSEFORCOMPUTER  = 0x1000,
  BIF_BROWSEFORPRINTER   = 0x2000,
  BIF_BROWSEINCLUDEFILES = 0x4000,
  BIF_SHAREABLE          = 0x8000
), pattern="BIF_*")
BIF.update (dict (USENEWUI = BIF.NEWDIALOGSTYLE | BIF.EDITBOX))
BIF.doc ("Styles for browsing for a folder")
BFFM = constants.Constants.from_pattern ("BFFM_*", namespace=shellcon)
BFFM.doc ("Part of the browse-for-folder shell mechanism")

CREDUI_FLAGS = constants.Constants.from_pattern ("CREDUI_FLAGS_*", namespace=win32cred)
CREDUI_FLAGS.doc ("Options for username prompt UI")
CRED_FLAGS = constants.Constants.from_pattern ("CRED_FLAGS_*", namespace=win32cred)
CRED_TYPE = constants.Constants.from_pattern ("CRED_TYPE_*", namespace=win32cred)
CRED_TI = constants.Constants.from_pattern ("CRED_TI_*", namespace=win32cred)

class x_dialogs (exc.x_winsys):
  "Base for dialog-related exceptions"

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_dialogs)

DESKTOP = wrapped (win32gui.GetDesktopWindow)

ENCODING = "UTF-8"

class _DropTarget (win32com.server.policy.DesignatedWrapPolicy):
  r"""Helper class to implement the IDropTarget interface so that
  files can be drag-dropped onto a text field in a dialog.
  """
  _reg_clsid_ = '{72AA1C07-73BA-4CA8-88B9-7F03FEA173E8}'
  _reg_progid_ = "WinSysDialogs.DropTarget"
  _reg_desc_ = "Drop target handler for WinSys Dialogs"
  _public_methods_ = ['DragEnter', 'DragOver', 'DragLeave', 'Drop']
  _com_interfaces_ = [pythoncom.IID_IDropTarget]

  _data_format = (
    win32con.CF_HDROP,
    None,
    pythoncom.DVASPECT_CONTENT,
    -1,
    pythoncom.TYMED_HGLOBAL
  )

  def __init__ (self, hwnd):
    self._wrap_ (self)
    self.hwnd = hwnd

  #
  # NB for the interface to work, all the functions must
  # be present even they do nothing.
  #
  def DragEnter (self, data_object, key_state, point, effect):
    r"""Query the data block for a drag action which is over the dialog.
    If we can handle it, indicate that we're ready to accept a drop from
    this data.
    """
    try:
      data_object.QueryGetData (self._data_format)
    except pywintypes.error:
      return shellcon.DROPEFFECT_NONE
    else:
      return shellcon.DROPEFFECT_COPY

  def Drop (self, data_object, key_state, point, effect):
    child_point = wrapped (win32gui.ScreenToClient, self.hwnd, point)
    child_hwnd = wrapped (win32gui.ChildWindowFromPoint, self.hwnd, child_point)
    data = data_object.GetData (self._data_format)
    n_files = shell.DragQueryFileW (data.data_handle, -1)
    if n_files:
      SendMessage (
        child_hwnd, win32con.WM_SETTEXT, None,
        utils.string_as_pointer (shell.DragQueryFileW (data.data_handle, 0).encode (ENCODING))
      )

  def DragOver (self, key_state, point, effect):
    r"""If there is a drag over one of the edit fields in the dialog
    indicate that we will accept a drop, otherwise not.
    """
    child_point = wrapped (win32gui.ScreenToClient, self.hwnd, point)
    child_hwnd = wrapped (win32gui.ChildWindowFromPoint, self.hwnd, child_point)
    class_name = wrapped (win32gui.GetClassName, child_hwnd)
    return shellcon.DROPEFFECT_COPY if class_name == "Edit" else shellcon.DROPEFFECT_NONE

  def DragLeave (self):
    r"""Do nothing, but the method must be implemented.
    """
    pass

def as_code (text):
  return text.lower ().replace (" ", "")

def _register_wndclass ():
  r"""Register a simple window with default cursor, icon, etc.
  """
  class_name = str (uuid.uuid1 ())
  wc = wrapped (win32gui.WNDCLASS)
  wc.SetDialogProc ()
  wc.hInstance = win32gui.dllhandle
  wc.lpszClassName = class_name
  wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
  wc.hCursor = wrapped (win32gui.LoadCursor, 0, win32con.IDC_ARROW)
  wc.hbrBackground = win32con.COLOR_WINDOW + 1
  wc.lpfnWndProc = {}
  wc.cbWndExtra = win32con.DLGWINDOWEXTRA + struct.calcsize ("Pi")
  icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE

  python_exe = wrapped (win32api.GetModuleHandle, None)
  wc.hIcon = wrapped (win32gui.LoadIcon, python_exe, 1)
  class_atom = wrapped (win32gui.RegisterClass, wc)
  return class_name

_class_name = _register_wndclass ()

#
# Convenience functions for frequently-wrapped API calls
#
def SendMessage (*args, **kwargs):
  return wrapped (win32gui.SendMessage, *args, **kwargs)

def PostMessage (*args, **kwargs):
  return wrapped (win32gui.PostMessage, *args, **kwargs)

def MoveWindow (*args, **kwargs):
  return wrapped (win32gui.MoveWindow, *args, **kwargs)

class BaseDialog (object):
  r"""Basic template for a dialog with one or more fields plus
  [Ok] and [Cancel] buttons. A simple spacing / sizing algorithm
  is used. Most of the work is done inside :meth:`_get_dialog_template`
  which examines the incoming fields and tries to place them according
  to their various options.
  """

  #
  # User messages to handle the progress aspect of the dialog
  #
  WM_PROGRESS_MESSAGE = win32con.WM_USER + 1
  WM_PROGRESS_COMPLETE = win32con.WM_USER + 2

  #
  # Fields, labels & callback buttons are created
  # in a regular way so they can be determined again
  # by their offset from the base.
  #
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

  MAX_W = 640
  MAX_H = 480

  #
  # Default styles
  #

  #
  # Only the standard Ok & Cancel buttons are allowed
  #
  BUTTONS = [("Cancel", win32con.IDCANCEL), ("Ok", win32con.IDOK)]

  def __init__ (self, title, parent_hwnd=0):
    r"""Initialise the dialog with a title and a list of fields of
    the form [(label, default), ...].
    """
    wrapped (win32gui.InitCommonControls)
    wrapped (pythoncom.OleInitialize)
    self.hinst = win32gui.dllhandle
    self.title = title
    self.parent_hwnd = parent_hwnd
    self.fields = []
    self._progress_id = None

  def _get_dialog_template (self):
    r"""Put together a sensible default layout for this dialog, taking
    into account the default structure and the (variable) number of fields.

    NB Although sensible default positions are chosen here, the horizontal
    layout will be overridden by the :meth:`_resize` functionality below.
    """
    dlg_class_name = _register_wndclass ()
    style = functools.reduce (operator.or_, (
      win32con.WS_THICKFRAME,
      win32con.WS_POPUP,
      win32con.WS_VISIBLE,
      win32con.WS_CAPTION,
      win32con.WS_SYSMENU,
      win32con.DS_SETFONT,
      win32con.WS_MINIMIZEBOX
    ))
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE

    n_fields = len (self.fields) + (1 if self.progress_callback else 0)
    dlg = []

    control_t = self.GUTTER_H
    for i, (field, default_value, callback) in enumerate (self.fields):
      label_l = self.GUTTER_W
      label_t = control_t
      field_l = label_l + self.LABEL_W + self.GUTTER_W
      field_t = label_t
      display_h = field_h = self.CONTROL_H

      if field is None:
        field_type, sub_type = "EDIT", "READONLY"
      elif isinstance (default_value, bool):
        field_type, sub_type = "BUTTON", "CHECKBOX"
      elif isinstance (default_value, tuple):
        field_type, sub_type = "BUTTON", "RADIOBUTTON"
      elif isinstance (default_value, list):
        field_type, sub_type = "COMBOBOX", None
      else:
        field_type, sub_type = "EDIT", None

      dlg.append (["STATIC", field, self.IDC_LABEL_BASE + i, (label_l, label_t, self.LABEL_W, self.CONTROL_H), cs | win32con.SS_LEFT])
      if field_type != "STATIC":
        field_styles = win32con.WS_TABSTOP
      else:
        field_styles = 0
      if (field_type, sub_type) == ("BUTTON", "CHECKBOX"):
        field_styles |= win32con.BS_AUTOCHECKBOX
        field_w = self.CONTROL_H
      elif (field_type, sub_type) == ("BUTTON", "RADIOBUTTON"):
        field_styles |= win32con.BS_AUTORADIOBUTTON
        field_w = self.CONTROL_H
      elif field_type == "COMBOBOX":
        if callback is not None:
          raise x_dialogs ("Cannot combine a list with a callback")
        field_styles |= win32con.CBS_DROPDOWNLIST
        field_w = self.FIELD_W
        field_h = 4 * self.CONTROL_H
        display_h = self.CONTROL_H
      elif field_type == "EDIT":
        field_styles |= win32con.WS_BORDER | win32con.ES_AUTOHSCROLL | win32con.ES_AUTOVSCROLL
        field_w = self.FIELD_W - ((self.CALLBACK_W) if callback else 0)
        if "\r\n" in str (default_value):
          field_styles |= win32con.ES_MULTILINE
          display_h = field_h = self.CONTROL_H * min (default_value.count ("\r\n"), 10)
        if sub_type == "READONLY":
          field_styles |= win32con.ES_READONLY
      else:
        raise x_dialogs ("Problemo", "_get_dialog_template", 0)

      dlg.append ([field_type, None, self.IDC_FIELD_BASE + i, (field_l, field_t, field_w, field_h), cs | field_styles])
      if callback:
        dlg.append (["BUTTON", "...", self.IDC_CALLBACK_BASE + i, (field_l + field_w + self.GUTTER_W, field_t, self.CALLBACK_W, self.CONTROL_H), cs | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON])

      control_t += display_h + self.GUTTER_H

    i += 1
    if self.progress_callback:
      self._progress_id = self.IDC_FIELD_BASE + i
      field_t = control_t
      field_w = self.W - (2 * self.GUTTER_W)
      field_l = self.GUTTER_W
      field_h = self.CONTROL_H
      field_styles = win32con.SS_LEFT
      dlg.append (["STATIC", None, self.IDC_FIELD_BASE + i, (field_l, field_t, field_w, field_h), cs | field_styles])
      control_t += field_h + self.GUTTER_H

    cs = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON
    button_t = control_t
    for i, (caption, id) in enumerate (reversed (self.BUTTONS)):
      field_h = self.CONTROL_H
      dlg.append (["BUTTON", caption, id, (self.W - ((i + 1) * (self.GUTTER_W + self.BUTTON_W)), button_t, self.BUTTON_W, field_h), cs])
    control_t += field_h + self.GUTTER_H

    dlg.insert (0, [self.title, (0, 0, self.W, control_t), style, None, (9, "Lucida Sans str"), None, dlg_class_name])
    return dlg

class Dialog (BaseDialog):
  r"""A general-purpose dialog class for collecting arbitrary information in
  text strings and handing it back to the user. Only Ok & Cancel buttons are
  allowed, and all the fields are considered to be strings. The list of
  fields is of the form: [(label, default), ...] and the values are saved
  in the same order.
  """
  def __init__ (self, title, fields, progress_callback=core.UNSET, parent_hwnd=0):
    r"""Initialise the dialog with a title and a list of fields of
    the form [(label, default), ...].
    """
    BaseDialog.__init__ (self, title, parent_hwnd)
    self.progress_callback = progress_callback
    self.fields = list (fields)
    if not self.fields:
      raise RuntimeError ("Must pass at least one field")
    self.results = []
    self.progress_thread = core.UNSET
    self.progress_cancelled = win32event.CreateEvent (None, 1, 0, None)

  def run (self):
    r"""The heart of the dialog box functionality. The call to DialogBoxIndirect
    kicks off the dialog's message loop, finally returning via the EndDialog call
    in OnCommand
    """
    message_map = {
      win32con.WM_COMMAND: self.OnCommand,
      win32con.WM_INITDIALOG: self.OnInitDialog,
      win32con.WM_SIZE: self.OnSize,
      win32con.WM_GETMINMAXINFO : self.OnMinMaxInfo,
      self.WM_PROGRESS_MESSAGE : self.OnProgressMessage,
      self.WM_PROGRESS_COMPLETE : self.OnProgressComplete
    }
    return wrapped (
      win32gui.DialogBoxIndirect,
      self.hinst,
      self._get_dialog_template (),
      self.parent_hwnd,
      message_map
    )

  def corners (self, l, t, r, b):
    r"""Designed to be subclassed (eg by :class:`InfoDialog`). By
    default simply returns the values unchanged.
    """
    return l, t, r, b

  def OnInitDialog (self, hwnd, msg, wparam, lparam):
    r"""Attempt to position the dialog box more or less in
    the middle of its parent (possibly the desktop). Then
    force a resize of the dialog controls which should take
    into account the different label lengths and the dialog's
    new size.
    """
    self.hwnd = hwnd

    #
    # If you want to have a translucent dialog,
    # enable the next block.
    #
    if False:
      wrapped (
        win32gui.SetWindowLong,
        self.hwnd,
        win32con.GWL_EXSTYLE,
        win32con.WS_EX_LAYERED | wrapped (
          win32gui.GetWindowLong,
          self.hwnd,
          win32con.GWL_EXSTYLE
        )
      )
      wrapped (
        win32gui.SetLayeredWindowAttributes,
        self.hwnd,
        255,
        (255 * 80) / 100,
        win32con.LWA_ALPHA
      )

    pythoncom.RegisterDragDrop (
      hwnd,
      pythoncom.WrapObject (
        _DropTarget (hwnd),
        pythoncom.IID_IDropTarget,
        pythoncom.IID_IDropTarget
      )
    )

    for i, (field, default, callback) in enumerate (self.fields):
      id = self.IDC_FIELD_BASE + i
      self._set_item (id, default)

    parent = self.parent_hwnd or DESKTOP
    l, t, r, b = self.corners (*wrapped (win32gui.GetWindowRect, self.hwnd))
    r = min (r, l + self.MAX_W)

    dt_l, dt_t, dt_r, dt_b = wrapped (win32gui.GetWindowRect, parent)
    centre_x, centre_y = wrapped (win32gui.ClientToScreen, parent, (round ((dt_r - dt_l) / 2), round ((dt_b - dt_t) / 2)))
    wrapped (win32gui.MoveWindow, self.hwnd, round (centre_x - (r / 2)), round (centre_y - (b / 2)), r - l, b - t, 0)
    l, t, r, b = wrapped (win32gui.GetClientRect, self.hwnd)
    self._resize (r - l, b - t, 0)
    return True

  def _resize (self, dialog_w, dialog_h, repaint=1):
    r"""Attempt to resize the controls on the dialog, spreading
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
    try:
      label_w, label_h = max (wrapped (win32gui.GetTextExtentPoint32, hDC, label or "") for label, _, _ in self.fields)
    finally:
      wrapped (win32gui.ReleaseDC, self.hwnd, hDC)

    for i, (field, default, callback) in enumerate (self.fields):
      if field is not None:
        label, l, t, r, b = coords (self.hwnd, self.IDC_LABEL_BASE + i)
        wrapped (win32gui.MoveWindow, label, self.GUTTER_W, t, label_w, b - t, repaint)
        label_r = self.GUTTER_W + label_w

        if callback:
          callback_button, l, t, r, b = coords (self.hwnd, self.IDC_CALLBACK_BASE + i)
          callback_w = r - l
          callback_l = dialog_w - self.GUTTER_W - callback_w
          MoveWindow (callback_button, callback_l, t, r - l, b - t, repaint)
        else:
          callback_w = 0
      else:
        label_r = callback_w = 0

      field, l, t, r, b = coords (self.hwnd, self.IDC_FIELD_BASE + i)
      field_l = label_r + self.GUTTER_W
      field_w = dialog_w - self.GUTTER_W - field_l - (callback_w + self.GUTTER_W if callback_w else 0)
      MoveWindow (field, field_l, t, field_w, b - t, repaint)

    if self._progress_id:
      field, l, t, r, b = coords (self.hwnd, self._progress_id)
      field_w = dialog_w - 2 * self.GUTTER_W
      MoveWindow (field, l, t, field_w, b - t, repaint)

    for i, (caption, id) in enumerate (reversed (self.BUTTONS)):
      button, l, t, r, b = coords (self.hwnd, id)
      MoveWindow (button, dialog_w - ((i + 1) * (self.GUTTER_W + (r - l))), t, r - l, b - t, repaint)

  def _get_item (self, item_id):
    r"""Return the current value of an item in the dialog.
    """
    hwnd = wrapped (win32gui.GetDlgItem, self.hwnd, item_id)
    class_name = wrapped (win32gui.GetClassName, hwnd)
    if class_name == "Edit":
      try:
        #
        # There is a bug/feature which prevents empty dialog items
        # from having their text read. Assume any error means that
        # the control is empty.
        #
        return wrapped (win32gui.GetDlgItemText, self.hwnd, item_id).decode ("mbcs")
      except:
        return ""
    elif class_name == "Button":
      return bool (SendMessage (hwnd, win32con.BM_GETCHECK, 0, 0))
    elif class_name == "ComboBox":
      field, default, callback = self.fields[item_id - self.IDC_FIELD_BASE]
      return default[SendMessage (hwnd, win32con.CB_GETCURSEL, 0, 0)]
    elif class_name == "Static":
      return None
    else:
      raise RuntimeError ("Unknown class: %s" % class_name)

  def _set_item (self, item_id, value):
    r"""Set the current value of an item in the dialog
    """
    item_hwnd = wrapped (win32gui.GetDlgItem, self.hwnd, item_id)
    class_name = wrapped (win32gui.GetClassName, item_hwnd)
    styles = wrapped (win32gui.GetWindowLong, self.hwnd, win32con.GWL_STYLE)
    if class_name == "Edit":
      if isinstance (value, datetime.date):
        value = value.strftime ("%d %b %Y")
      value = str (value).replace ("\r\n", "\n").replace ("\n", "\r\n")
      wrapped (win32gui.SetDlgItemText, self.hwnd, item_id, value)
    elif class_name == "Button":
      #~ if styles & win32con.BS_CHECKBOX:
      SendMessage (item_hwnd, win32con.BM_SETCHECK, int (value), 0)
      #~ elif styles & win32con.BS_RADIOBUTTON:
    elif class_name == "ComboBox":
      for item in value:
        if isinstance (item, tuple):
          item = item[0]
        SendMessage (item_hwnd, win32con.CB_ADDSTRING, 0, utils.string_as_pointer (str (item)))
      SendMessage (item_hwnd, win32con.CB_SETCURSEL, 0, 0)
    elif class_name == "Static":
      wrapped (win32gui.SetDlgItemText, self.hwnd, item_id, str (value))
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
    r"""Prevent the dialog from resizing vertically by extracting
    the window's current size and using the minmaxinfo message
    to set the maximum & minimum window heights to be its current height.
    """
    dlg_l, dlg_t, dlg_r, dlg_b = wrapped (win32gui.GetWindowRect, hwnd)
    #
    # If returning from minmization, do nothing
    #
    if wrapped (win32gui.GetClientRect, hwnd) == (0, 0, 0, 0):
      return 0
    #
    # MINMAXINFO is a struct of 5 POINT items, each of which
    # is a pair of LONGs. We extract the structure into a list,
    # set the Y coord of MaxTrackSize and of MinTrackSize to be
    # the window's current height and write the data back into
    # the same place.
    #
    POINT_FORMAT = "LL"
    MINMAXINO_FORMAT = 5 * POINT_FORMAT
    data = win32gui.PyGetMemory (lparam, struct.calcsize (MINMAXINO_FORMAT))
    minmaxinfo = list (struct.unpack (MINMAXINO_FORMAT, data))
    minmaxinfo[9] = minmaxinfo[7] = dlg_b - dlg_t
    win32gui.PySetMemory (lparam, struct.pack (MINMAXINO_FORMAT, *minmaxinfo))
    return 0

  def _enable (self, id, allow=True):
    r"""Convenience function to enable or disable a control by id
    """
    wrapped (
      win32gui.EnableWindow,
      wrapped (win32gui.GetDlgItem, self.hwnd, id),
      allow
    )

  def OnProgressMessage (self, hwnd, msg, wparam, lparam):
    r"""Respond to a progress update from within the progress
    thread. LParam will be a pointer to a string containing
    a utf8-encoded string which is to be displayed in the
    dialog's progress static.
    """
    message = marshal.loads (win32gui.PyGetMemory (lparam, wparam))
    self._set_item (self._progress_id, message)

  def OnProgressComplete (self, hwnd, msg, wparam, lparam):
    r"""Respond to the a message signalling that all processing is
    now complete by re-enabling the ok button, disabling cancel,
    and setting focus to the ok so a return or space will close
    the dialog.
    """
    message = marshal.loads (win32gui.PyGetMemory (lparam, wparam))
    self._set_item (self._progress_id, message)
    self._enable (win32con.IDCANCEL, False)
    self._enable (win32con.IDOK, True)
    wrapped (win32gui.SetFocus, wrapped (win32gui.GetDlgItem, hwnd, win32con.IDOK))

  def _progress_complete (self, message):
    r"""Convenience function to tell the dialog that progress is complete,
    passing a message along which will be displayed in the progress box
    """
    print ("_progress_complete", message)
    _message = marshal.dumps (message)
    print ("_message", _message)
    address, length = win32gui.PyGetBufferAddressAndLen (_message)
    print ("addr, len", address, length)
    SendMessage (self.hwnd, self.WM_PROGRESS_COMPLETE, length, address)

  def _progress_message (self, message):
    r"""Convenience function to send progress messages to the dialog
    """
    _message = marshal.dumps (message)
    address, length = win32gui.PyGetBufferAddressAndLen (_message)
    SendMessage (self.hwnd, self.WM_PROGRESS_MESSAGE, length, address)

  def OnOk (self, hwnd):
    r"""When OK is pressed, if this isn't a progress dialog then simply
    gather the results and return. If this is a progress dialog then
    start a thread to handle progress via the progress iterator.
    """
    def progress_thread (iterator, cancelled):
      r"""Handle the progress side of the dialog by iterating over a supplied
      iterator (presumably a generator) sending generated values as messages
      to the progress box -- these might be percentages or files processed
      or whatever.

      If the user cancels, an event will be fired which is detected here and
      the iteration broken. Likewise an exception will be logged to the usual
      places and a suitable message sent.
      """
      try:
        for message in iterator:
          if wrapped (win32event.WaitForSingleObject, cancelled, 0) != win32event.WAIT_TIMEOUT:
            self._progress_complete ("User cancelled")
            break
          else:
            self._progress_message (message)
      except:
        info_dialog (
          "An error occurred: please contact the Helpdesk",
          traceback.format_exc (),
          hwnd
        )
        self._progress_complete ("An error occurred")
      else:
        self._progress_complete ("Complete")

    #
    # Gather results from fields in the order they were entered
    #
    self.results = []
    for i, (field, default_value, callback) in enumerate (self.fields):
      value = self._get_item (self.IDC_FIELD_BASE + i)
      if isinstance (default_value, datetime.date):
        try:
          value = datetime.datetime.strptime (value, "%d %b %Y").date ()
        except ValueError:
          win32api.MessageBox (
            hwnd,
            "Dates must look like:\n%s" % datetime.date.today ().strftime ("%d %b %Y").lstrip ("0"),
            "Invalid Date"
          )
          return

      self.results.append (value)

    #
    # If this is a progress dialog, disable everything except the
    # Cancel button and start a thread which will loop over the
    # iterator keeping an eye out for a cancel event.
    #
    if self.progress_callback:
      self._set_item (self._progress_id, "Working...")
      for i in range (len (self.fields)):
        self._enable (self.IDC_FIELD_BASE + i, False)
      self._enable (win32con.IDOK, False)
      wrapped (win32gui.SetFocus, wrapped (win32gui.GetDlgItem, hwnd, win32con.IDCANCEL))
      progress_iterator = self.progress_callback (*self.results)
      self.progress_callback = None
      self.progress_thread = threading.Thread (
        target=progress_thread,
        args=(progress_iterator, self.progress_cancelled)
      )
      self.progress_thread.setDaemon (True)
      self.progress_thread.start ()

    #
    # Either this isn't a progress dialog or the progress is
    # complete. In either event, close the dialog with an OK state.
    #
    else:
      wrapped (win32gui.EndDialog, hwnd, win32con.IDOK)

  def OnCancel (self, hwnd):
    r"""If the user presses cancel check to see whether we're running within
    a progress thread. If so, set the cancel event and wait for the thread
    to catch up. Either way, close the dialog with a cancelled state.
    """
    self.results = []
    if self.progress_thread:
      win32event.SetEvent (self.progress_cancelled),
      self._set_item (self._progress_id, "Cancelling...")
      self.progress_thread.join ()
    wrapped (win32gui.EndDialog, hwnd, win32con.IDCANCEL)

  def OnCallback (self, hwnd, field_id):
    r"""If the user pressed a callback button associated with a text
    field, find the field and call its callback with the dialog window
    and the field's current value. If anything is returned, put that
    value back into the field.
    """
    field, default, callback = self.fields[field_id - self.IDC_FIELD_BASE]
    result = callback (hwnd, self._get_item (field_id))
    if result:
      self._set_item (field_id, result)

  def OnCommand (self, hwnd, msg, wparam, lparam):
    r"""Handle button presses: OK, Cancel and the callback buttons
    which are optional for text fields
    """
    id = win32api.LOWORD (wparam)
    if id == win32con.IDOK:
      self.OnOk (hwnd)
    elif id == win32con.IDCANCEL:
      self.OnCancel (hwnd)
    elif self.IDC_CALLBACK_BASE <= id < (self.IDC_CALLBACK_BASE + len (self.fields)):
      self.OnCallback (hwnd, self.IDC_FIELD_BASE + id - self.IDC_CALLBACK_BASE)

def _fields_to_fields (fields):
  """Helper function to transform a list of possibly 2-tuple field
  tuples into 3-tuples
  """
  _fields = []
  for field in fields:
    if len (field) < 3:
      _fields.append (tuple (field) + (None,))
    else:
      _fields.append (tuple (field))
  return _fields

def dialog (title, *fields):
  """Shortcut function to populate and run a dialog, returning
  the button pressed and values saved. After the title, the
  function expects a series of 2-tuples where the first item
  is the field label and the second is the default value. This
  default value determines the type of ui element as follows:

  * list - a drop down list in the order given
  * bool - a checkbox
  * string - an edit control

  A third item may be present in the tuple where the second item
  is a string. This is a callback function. If this is present and
  is not None, a small button will be added to the right of the
  corresponding edit control which, when pressed, will call the
  callback which must return a string to be inserted in the edit
  control, or None if no change is to be made. This is intended
  to throw up, eg, a file-browse dialog. A useful default is
  available as :func:`get_filename`.

  :param title: any string to use as the title of the dialog
  :param fields: series of 2-tuples consisting of a name and a default value.
  :returns: the values entered by the user in the order of `fields`
  """
  d = Dialog (title, _fields_to_fields (fields))
  d.run ()
  return d.results

def progress_dialog (title, progress_callback, *fields):
  """Populate and run a dialog with a progress
  callback which yields messages. Fields are the same as for
  :func:`dialog` but the second parameter is a function which
  takes the value list as parameters and yields strings as updates.
  The strings will be displayed in a static control on the dialog
  while the [Ok] button is disabled until the callback completes,
  at which point the [Ok] button is enabled again and the tuple
  of values is returned to the caller.

  ..  note::

      The progress callback runs inside a thread so any necessary
      thread-specific preparation must happen, eg invoking
      pythoncom.CoInitialize.

  This example takes a directory from the user and finds the total
  size of each of its subdirectories, showing the name of each one
  as it is searched. Finally, it uses :func:`utils.size_as_mb` to
  display a human-redable version of each directory size::

    from winsys import dialogs, fs, utils

    sizes = {}
    def sizer (root):
      for d in fs.dir (root).dirs ():
        yield d.name
        sizes[d] = sum (f.size for f in d.flat ())

    dialogs.progress_dialog (
      "Sizer",
      sizer,
      ("Root", "c:/temp", dialogs.get_folder)
    )

    for d, size in sorted (sizes.items ()):
      print d.name, "=>", utils.size_as_mb (size)

  :param title: any string to use as the title of the dialog
  :param progress_callback: a function accepting values as per `fields` and yielding progress as strings
  :param fields: series of 2-tuples consisting of a name and a default value
  :returns: the values entered by the user in the order of `fields`
  """
  d = Dialog (title, _fields_to_fields (fields), progress_callback=progress_callback)
  d.run ()
  return d.results

def info_dialog (title, text, hwnd=core.UNSET):
  """A dialog with no fields which simply displays information
  in a read-only multiline edit box. The text can be arbitrarily big
  but the dialog will only adjust vertically up to a certain point.
  After that the user may scroll with the keyboard. The text can be
  selected and copied::

    import os, sys
    from winsys import dialogs
    filepath = os.path.join (sys.prefix, "LICENSE.txt")
    dialogs.info_dialog ("LICENSE.txt", open (filepath).read ())

  :param title: any string to use as the title of the dialog
  :param info: any (possibly multiline) string to display in the body of the dialog
  :param parent_hwnd: optional window handle
  """
  InfoDialog (title, text, hwnd).run ()

def get_folder (hwnd=None, start_folder=None):
  """Quick interface to the shell's browse-for-folder dialog,
  optionally starting in a particular folder.

  ..  warning::
      At present this interacts badly with TortoiseHg, causing the
      interpreter to stack dump.
  """
  def _set_start_folder (hwnd, msg, lp, data):
    if msg == BFFM.INITIALIZED and data:
      SendMessage (hwnd, BFFM.SETSELECTION, 1, utils.string_as_pointer (data))

  pythoncom.CoInitialize ()
  try:
    pidl, display_name, image_list = wrapped (
      shell.SHBrowseForFolder,
      hwnd or DESKTOP,
      None,
      "Select a file or folder",
      BIF.USENEWUI | BIF.SHAREABLE,
      _set_start_folder,
      start_folder
    )
  finally:
    pythoncom.CoUninitialize ()

  if (pidl, display_name, image_list) == (None, None, None):
    return None
  else:
    return wrapped (shell.SHGetPathFromIDList, pidl)

def get_filename (hwnd=None, start_folder=None):
  """Quick interface to the shell's browse-for-folder dialog,
  optionally starting in a particular folder and allowing file
  and share selection.

  ..  warning::
      At present this interacts badly with TortoiseHg, causing the
      interpreter to stack dump.
  """
  def _set_start_folder (hwnd, msg, lp, data):
    if msg == BFFM.INITIALIZED and data:
      SendMessage (hwnd, BFFM.SETSELECTION, 1, utils.string_as_pointer (data))

  pythoncom.CoInitialize ()
  try:
    pidl, display_name, image_list = wrapped (
      shell.SHBrowseForFolder,
      hwnd,
      None,
      "Select a file or folder",
      BIF.BROWSEINCLUDEFILES | BIF.USENEWUI | BIF.SHAREABLE,
      _set_start_folder if start_folder else None,
      start_folder
    )
  finally:
    pythoncom.CoUninitialize ()

  if (pidl, display_name, image_list) == (None, None, None):
    return None
  else:
    return wrapped (shell.SHGetPathFromIDList, pidl)

class InfoDialog (Dialog):

  def __init__ (self, title, info, parent_hwnd=core.UNSET):
    if parent_hwnd is core.UNSET:
      parent_hwnd = DESKTOP
    self.info = str (info).replace ("\r\n", "\n").replace ("\n", "\r\n")
    Dialog.__init__ (self, title, [(None, self.info, None)], parent_hwnd=parent_hwnd)
    self.BUTTONS = [("Ok", win32con.IDOK)]

  def OnOk (self, hwnd):
    wrapped (win32gui.EndDialog, hwnd, win32con.IDOK)

  def corners (self, l, t, r, b):
    """Called when the dialog is first initialised: estimate how wide
    the dialog should be according to the longest line of text
    """
    hDC = wrapped (win32gui.GetDC, self.hwnd)
    try:
      w, h = max (wrapped (win32gui.GetTextExtentPoint32, hDC, line) for line in self.info.split ("\r\n"))
      return l, t, l + w + 2 * self.GUTTER_W, b
    finally:
      wrapped (win32gui.ReleaseDC, self.hwnd, hDC)

def get_password (name="", domain=""):
  flags = 0
  flags |= CREDUI_FLAGS.GENERIC_CREDENTIALS
  flags |= CREDUI_FLAGS.DO_NOT_PERSIST
  _, password, _ = wrapped (
    win32cred.CredUIPromptForCredentials,
    domain,
    0,
    name,
    None,
    True,
    flags,
    {}
  )
  return password
