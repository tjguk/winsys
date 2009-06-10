# -*- coding: iso-8859-1 -*-
import win32api
import win32profile
import win32gui
import win32con
import winerror

from winsys import constants, core, exc, security, utils, registry

class x_env (exc.x_winsys):
  "Base exception for all env exceptions"

WINERROR_MAP = {
  winerror.ERROR_ENVVAR_NOT_FOUND : exc.x_not_found,
}
wrapped = exc.wrapper (WINERROR_MAP, x_env)

class Env (core._WinSysObject):
  
  def keys (self):
    raise NotImplementedError
  
  def items (self):
    raise NotImplementedError
  
  def __getitem__ (self, item):
    raise NotImplementedError
  
  def __setitem__ (self, item, value):
    raise NotImplementedError
  
  def get (self, item, default=None):
    try:
      return self[item]
    except KeyError:
      return default
  
  def update (self, dict_initialiser):
    for k, v in dict (dict_initialiser).items ():
      self[k] = v
  
  def __repr__ (self):
    return repr (dict (self.items ()))

class Process (Env):
  
  def __init__ (self):
    super (Process, self).__init__ ()
    
  def keys (self):
    return wrapped (win32profile.GetEnvironmentStrings).keys ()
  
  def items (self):
    return wrapped (win32profile.GetEnvironmentStrings).items ()
  
  def __getitem__ (self, item):
    value = wrapped (win32api.GetEnvironmentVariable, item)
    if value is None:
      raise KeyError
    else:
      return value
    
  def __setitem__ (self, item, value):
    return wrapped (win32api.SetEnvironmentVariable, item, unicode (value))
    
    
class Persistent (Env):
  
  root = None
  
  @staticmethod
  def broadcast ():
    win32gui.SendMessageTimeout (
      win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 
      0, "Environment", 
      win32con.SMTO_ABORTIFHUNG, 2000
    )

  def __init__ (self):
    super (Persistent, self).__init__ ()
    self.registry = registry.registry (self.root)
    
  def keys (self):
    return (name for name, value in self.registry.values ())
  
  def items (self):
    return self.registry.values ()
  
  def __getitem__ (self, item):
    try:
      return self.registry.get_value (item)
    except exc.x_not_found:
      raise KeyError
    
  def __setitem__ (self, item, value):
    self.registry.set_value (item, value)
    
  def __delitem__ (self, item):
    del self.registry[item]
    
class System (Persistent):
  root = r"HKLM\System\CurrentControlSet\Control\Session Manager\Environment"

class User (Persistent):
  root = ur"HKCU\Environment"
