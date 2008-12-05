# -*- coding: iso-8859-1 -*-
import os, sys
import marshal
import threading
import time

import pywintypes
import winerror
import win32gui
import win32con
import win32api

from winsys import core, exceptions, ipc, utils, dialogs

WINERROR_MAP = {
  winerror.ERROR_INVALID_WINDOW_HANDLE : exceptions.x_invalid_handle,
}
wrapped = exceptions.wrapper (WINERROR_MAP)

class MainWindow:
  
  def __init__ (self, title):
    wc = win32gui.WNDCLASS ()
    hinst = wc.hInstance = win32api.GetModuleHandle (None)
    wc.lpszClassName = "Log output window"
    wc.lpfnWndProc = self._wndproc_
    wc.hbrBackground = win32con.COLOR_WINDOW
    wc.hCursor = win32gui.LoadCursor (0, win32con.IDC_ARROW)
    wc.style = win32con.CS_OWNDC | win32con.CS_HREDRAW | win32con.CS_VREDRAW
    self.hEdit = None
    self.hwnd = win32gui.CreateWindowEx (
      win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_APPWINDOW,
      win32gui.RegisterClass (wc), 
      title, 
      win32con.WS_OVERLAPPEDWINDOW, 
      0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
      0, 0, 
      hinst, 
      None
    )
    self.hEdit = win32gui.CreateWindow (
      "EDIT", 
      None,
      win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_VSCROLL | win32con.ES_LEFT | win32con.ES_MULTILINE | win32con.ES_AUTOVSCROLL,
      0, 0, 0, 0,
      self.hwnd, 0,
      hinst,
      None
    )
    win32gui.ShowWindow (self.hwnd, win32con.SW_SHOWNORMAL)

  def _wndproc_ (self, hwnd, msg, wparam, lparam):
    if msg == win32con.WM_SIZE:
      win32gui.MoveWindow (self.hEdit, 0, 0, win32api.LOWORD (lparam), win32api.HIWORD (lparam), True)
    elif msg == win32con.WM_DESTROY:
      win32gui.PostQuitMessage (0)
    elif msg == win32con.WM_SETTEXT:
      self.output_message (win32gui.PyGetString (lparam))
    else:
      return win32gui.DefWindowProc (hwnd, msg, wparam, lparam)

  def output_message (self, string):
    string = string.replace ("\r\n", "\n").replace ("\n", "\r\n")
    hwnd = self.hEdit
    win32gui.SendMessage (hwnd, win32con.EM_SETREADONLY, 0, 0)
    win32gui.SendMessage (hwnd, win32con.WM_SETREDRAW, 0, 0)
    win32gui.SendMessage (hwnd, win32con.EM_REPLACESEL, 0, utils.string_as_pointer (string))
    win32gui.SendMessage (hwnd, win32con.EM_LINESCROLL, 0, win32gui.SendMessage (hwnd, win32con.EM_GETLINECOUNT, 0, 0))
    win32gui.SendMessage (hwnd, win32con.WM_SETREDRAW, 1, 0)
    win32gui.SendMessage (hwnd, win32con.EM_SETREADONLY, 1, 0)

def handle_mailslot (hwnd, mailslot_name):
  mailslot = ipc.mailslot (mailslot_name)
  while True:
    text = marshal.loads (mailslot.get ())
    if text is None:
      try:
        wrapped (win32gui.PostMessage, hwnd, win32con.WM_CLOSE, 0, 0)
      except exceptions.x_invalid_handle:
        pass
      break
    else:
      win32gui.SendMessage (hwnd, win32con.WM_SETTEXT, 0, utils.string_as_pointer (text + "\n"))
      
def main (mailslot_name):
  window = MainWindow ("Listening to mailslot %s" % mailslot_name)
  threading.Thread (target=handle_mailslot, args=(window.hwnd, mailslot_name)).start ()
  win32gui.PumpMessages ()
  try:
    ipc.Mailslot (mailslot_name).put (marshal.dumps (None))
  except exceptions.x_not_found:
    pass

if __name__=='__main__':
  if len (sys.argv) >= 2:
    mailslot_name = sys.argv[1]
  else:
    results = dialogs.dialog ("Mailslot name", ("Mailslot name", "\\\\.\\mailslot\\", None))
    if results:
      mailslot_name = results[0]
    else:
      sys.exit ()
  
  main (mailslot_name)
