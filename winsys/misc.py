# -*- coding: iso-8859-1 -*-
import os, sys
import time
import uuid

import win32console
import win32gui

from winsys import constants, core, utils, security
from winsys.exceptions import *

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
