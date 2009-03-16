import os, sys
import marshal
import operator
import pythoncom
import winxpgui as win32gui
import pythoncom
import win32com.server.policy
import win32api
import win32con
from win32com.shell import shell, shellcon
import win32ui
import struct
import threading
import traceback
import uuid

from winsys import core, constants, utils, ipc
from winsys.exceptions import *

#
# Constants used by SHBrowseForFolder
#
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
), pattern=u"BIF_*")
BIF.update (dict (USENEWUI = BIF.NEWDIALOGSTYLE | BIF.EDITBOX))
BFFM = constants.Constants.from_pattern (u"BFFM_*", namespace=shellcon)

class x_dialogs (x_winsys):
  pass

WINERROR_MAP = {
}
wrapped = wrapper (WINERROR_MAP, x_dialogs)

ENCODING = "UTF-8"

class DropTarget (win32com.server.policy.DesignatedWrapPolicy):
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
    child_point = wrapped (win32gui.ScreenToClient, self.hwnd, point)
    child_hwnd = wrapped (win32gui.ChildWindowFromPoint, self.hwnd, child_point)
    class_name = wrapped (win32gui.GetClassName, child_hwnd)
    return shellcon.DROPEFFECT_COPY if class_name == "Edit" else shellcon.DROPEFFECT_NONE
  
  def DragLeave (self):
    pass
  
def as_code (text):
  return text.lower ().replace (" ", "")

def _register_wndclass ():
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

def SendMessage (*args, **kwargs):
  return wrapped (win32gui.SendMessage, *args, **kwargs)
  
def PostMessage (*args, **kwargs):
  return wrapped (win32gui.PostMessage, *args, **kwargs)
  
def MoveWindow (*args, **kwargs):
  return wrapped (win32gui.MoveWindow, *args, **kwargs)

class BaseDialog (object):
  
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
    """Initialise the dialog with a title and a list of fields of
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
    """Put together a sensible default layout for this dialog, taking
    into account the default structure and the (variable) number of fields.
    
    NB Although sensible default positions are chosen here, the horizontal
    layout will be overridden by the _resize functionality below.
    """
    dlg_class_name = _register_wndclass ()
    style = reduce (operator.or_, (
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
        if "\r\n" in default_value:
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

    dlg.insert (0, [self.title, (0, 0, self.W, control_t), style, None, (9, "Lucida Sans Regular"), None, dlg_class_name])
    return dlg

class Dialog (BaseDialog):
  """A general-purpose dialog class for collecting arbitrary information in
  text strings and handing it back to the user. Only Ok & Cancel buttons are
  allowed, and all the fields are considered to be strings. The list of
  fields is of the form: [(label, default), ...] and the values are saved
  in the same order.
  """
  def __init__ (self, title, fields, progress_callback=core.UNSET, parent_hwnd=0):
    """Initialise the dialog with a title and a list of fields of
    the form [(label, default), ...].
    """
    BaseDialog.__init__ (self, title, parent_hwnd)
    self.progress_callback = progress_callback
    self.fields = list (fields)
    if not self.fields:
      raise RuntimeError ("Must pass at least one field")
    self.results = []
    self.progress_thread = core.UNSET
    self.progress_cancelled = ipc.event ()
    
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
    return l, t, r, b
  
  def OnInitDialog (self, hwnd, msg, wparam, lparam):
    """Attempt to position the dialog box more or less in
    the middle of its parent (possibly the desktop). Then
    force a resize of the dialog controls which should take
    into account the different label lengths and the dialog's
    new size.
    """
    self.hwnd = hwnd
    
    pythoncom.RegisterDragDrop (
      hwnd,
      pythoncom.WrapObject (
        DropTarget (hwnd),
        pythoncom.IID_IDropTarget,
        pythoncom.IID_IDropTarget
      )
    )

    for i, (field, default, callback) in enumerate (self.fields):
      id = self.IDC_FIELD_BASE + i
      self._set_item (id, default)
    
    parent = self.parent_hwnd or wrapped (win32gui.GetDesktopWindow)
    l, t, r, b = self.corners (*wrapped (win32gui.GetWindowRect, self.hwnd))
    r = min (r, l + self.MAX_W)
    
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
    hwnd = wrapped (win32gui.GetDlgItem, self.hwnd, item_id)
    class_name = wrapped (win32gui.GetClassName, hwnd)
    if class_name == "Edit":      
      try:
        #
        # There is a bug/feature which prevents empty dialog items
        # from having their text read. Assume any error means that
        # the control is empty.
        #
        return wrapped (win32gui.GetDlgItemText, self.hwnd, item_id)
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
    item_hwnd = wrapped (win32gui.GetDlgItem, self.hwnd, item_id)
    class_name = wrapped (win32gui.GetClassName, item_hwnd)
    styles = wrapped (win32gui.GetWindowLong, self.hwnd, win32con.GWL_STYLE)
    if class_name == "Edit":
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
    """Prevent the dialog from resizing vertically by extracting
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
    data = win32gui.PyGetString (lparam, struct.calcsize (MINMAXINO_FORMAT))
    minmaxinfo = list (struct.unpack (MINMAXINO_FORMAT, data))
    minmaxinfo[9] = minmaxinfo[7] = dlg_b - dlg_t
    win32gui.PySetMemory (lparam, struct.pack (MINMAXINO_FORMAT, *minmaxinfo))
    return 0

  def _enable (self, id, allow=True):
    """Convenience function to enable or disable a control by id
    """
    wrapped (
      win32gui.EnableWindow, 
      wrapped (win32gui.GetDlgItem, self.hwnd, id), 
      allow
    )
  
  def OnProgressMessage (self, hwnd, msg, wparam, lparam):
    """Respond to a progress update from within the progress
    thread. LParam will be a pointer to a string containing
    a utf8-encoded string which is to be displayed in the
    dialog's progress static.
    """
    message = marshal.loads (win32gui.PyGetString (lparam, wparam)) 
    self._set_item (self._progress_id, message)
    
  def OnProgressComplete (self, hwnd, msg, wparam, lparam):
    """Respond to the a message signalling that all processing is
    now complete by re-enabling the ok button, disabling cancel,
    and setting focus to the ok so a return or space will close
    the dialog.
    """
    message = marshal.loads (win32gui.PyGetString (lparam, wparam))
    self._set_item (self._progress_id, message)
    self._enable (win32con.IDCANCEL, False)
    self._enable (win32con.IDOK, True)
    wrapped (win32gui.SetFocus, wrapped (win32gui.GetDlgItem, hwnd, win32con.IDOK))

  def _progress_complete (self, message):
    """Convenience function to tell the dialog that progress is complete,
    passing a message along which will be displayed in the progress box
    """
    _message = buffer (marshal.dumps (message))
    address, length = win32gui.PyGetBufferAddressAndLen (_message)
    SendMessage (self.hwnd, self.WM_PROGRESS_COMPLETE, length, address)
    
  def _progress_message (self, message):
    """Convenience function to send progress messages to the dialog
    """
    _message = buffer (marshal.dumps (message))
    address, length = win32gui.PyGetBufferAddressAndLen (_message)
    SendMessage (self.hwnd, self.WM_PROGRESS_MESSAGE, length, address)
    
  def OnOk (self, hwnd):
    """When OK is pressed, if this isn't a progress dialog then simply
    gather the results and return. If this is a progress dialog then
    start a thread to handle progress via the progress iterator.
    """
    def progress_thread (iterator, cancelled):
      """Handle the progress side of the dialog by iterating over a supplied
      iterator (presumably a generator) sending generated values as messages
      to the progress box -- these might be percentages or files processed
      or whatever.
      
      If the user cancels an event will be fired which is detected here and
      the iteration broken. Likewise an exception will be logged to the usual
      places and a suitable message sent.
      """
      try:
        for message in iterator:
          if cancelled:
            self._progress_complete ("User cancelled")
            break
          else:
            self._progress_message (message)
      except:
        InfoDialog (  
          "An error occurred: please contact the Helpdesk", 
          traceback.format_exc (), 
          parent_hwnd=hwnd
        ).run ()
        self._progress_complete ("An error occurred")
      else:
        self._progress_complete ("Complete")

    #
    # Gather results from fields in the order they were entered
    #
    self.results = [self._get_item (self.IDC_FIELD_BASE + i) for i, field in enumerate (self.fields)]
      
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
      self.progress_thread.start ()
    
    #
    # Either this isn't a progress dialog or the progress is
    # complete. In either event, close the dialog with an OK state.
    #
    else:
      wrapped (win32gui.EndDialog, hwnd, win32con.IDOK)

  def OnCancel (self, hwnd):
    """If the user presses cancel check to see whether we're running within
    a progress thread. If so, set the cancel event and wait for the thread
    to catch up. Either way, close the dialog with a cancelled state.
    """
    self.results = []
    if self.progress_thread:
      self.progress_cancelled.set ()
      self._set_item (self._progress_id, "Cancelling...")
      self.progress_thread.join ()
    wrapped (win32gui.EndDialog, hwnd, win32con.IDCANCEL)

  def OnCallback (self, hwnd, field_id):
    """If the user pressed a callback button associated with a text
    field, find the field and call its callback with the dialog window
    and the field's current value. If anything is returned, put that
    value back into the field.
    """
    field, default, callback = self.fields[field_id - self.IDC_FIELD_BASE]
    result = callback (hwnd, self._get_item (field_id))
    if result:
      self._set_item (field_id, result)

  def OnCommand (self, hwnd, msg, wparam, lparam):
    """Handle button presses: OK, Cancel and the callback buttons
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
  the button pressed and values saved.
  """
  d = Dialog (title, _fields_to_fields (fields))
  d.run ()
  return d.results

def progress_dialog (title, progress_callback, *fields):
  """Shortcut function to populate an run a dialog with a progress
  callback which must yield messages
  """
  d = Dialog (title, _fields_to_fields (fields), progress_callback=progress_callback)
  d.run ()
  return d.results

def get_filename (start_folder=None, hwnd=None):
  """Quick interface to the shell's browse-for-folder dialog,
  optionally starting in a particular folder and allowing file
  and share selection.
  """
  def _set_start_folder (hwnd, msg, lp, data):
    if msg == BFFM.INITIALIZED and data:
      SendMessage (hwnd, BFFM.SETSELECTION, 1, utils.string_as_pointer (data))
  
  pythoncom.CoInitialize ()
  try:
    pidl, display_name, image_list = wrapped (
      shell.SHBrowseForFolder,
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
    return wrapped (shell.SHGetPathFromIDList, pidl)

class InfoDialog (Dialog):

  def __init__ (self, title, info, parent_hwnd=0):
    self.info = str (info).replace ("\r\n", "\n").replace ("\n", "\r\n")
    Dialog.__init__ (self, title, [(None, self.info, None)], parent_hwnd=parent_hwnd)
    self.BUTTONS = [("Ok", win32con.IDOK)]

  def OnOk (self, hwnd):
    wrapped (win32gui.EndDialog, hwnd, win32con.IDOK)
    
  def corners (self, l, t, r, b):
    hDC = wrapped (win32gui.GetDC, self.hwnd)
    try:
      w, h = max (wrapped (win32gui.GetTextExtentPoint32, hDC, line) for line in self.info.split ("\r\n"))
      return l, t, l + w + 2 * self.GUTTER_W, b
    finally:
      wrapped (win32gui.ReleaseDC, self.hwnd, hDC)

if __name__=='__main__':
  from winsys import fs
  import csv
  
  def _get_filename (hwnd, data): 
    return get_filename (data, hwnd)

  #~ def progress_callback (root, csv_filename):
    #~ fsroot = fs.Dir (root)
    #~ with open (csv_filename, "wb") as f:
      #~ writer = csv.writer (f)
      #~ for dir in fsroot.dirs ():
        #~ yield dir
        #~ writer.writerows ([[f] for f in dir.files ()])
        
  def progress_callback (*args):
    import time
    for i in u"The quick brown fox jumps over the lazy dog".split ():
      yield i
      time.sleep (0.5)

  #~ print dialog (
    #~ "Test", 
    #~ ('Root', r'\\vogbs022\user', _get_filename), 
    #~ ('Ignore access errors', True), 
    #~ ('Size Threshold (Mb)', '100')
  #~ )  
  #~ print dialog ("Test2", ("Scan from:", r"c:\temp", _get_filename), ("List of things", ['Timothy', 'John', 'Golden']))
  print progress_dialog ("Test4", progress_callback, ("Root", "c:/temp"), ("Output .csv", "c:/temp/temp.csv"))
