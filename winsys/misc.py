# -*- coding: iso-8859-1 -*-
import os, sys
import time
import uuid

import win32api
import win32con
import win32gui
import win32console
import win32gui

from winsys import core, registry

def set_console_title (text):
  title = win32console.GetConsoleTitle ()
  win32console.SetConsoleTitle (text)
  return title

def console_hwnd ():
  title = uuid.uuid1 ().hex
  old_title = set_console_title (title)
  try:
    time.sleep (0.05)
    return win32gui.FindWindow (None, title)
  finally:
    set_console_title (old_title)

def set_environment (**kwargs):
  root = registry.registry ("HKCU")
  env = root.Environment
  for label, value in kwargs.items ():
    env.set_value (label, value)
  win32gui.SendMessageTimeout (
    win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 
    0, "Environment", 
    win32con.SMTO_ABORTIFHUNG, 2000
  )

def get_environment ():
  return dict (
    registry.registry (r"HKCU\Environment").values ()
  )
