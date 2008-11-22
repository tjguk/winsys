# -*- coding: iso-8859-1 -*-
import os, sys
import operator
import re

import winerror
import win32api
import pywintypes

from winsys import core, utils, security
from winsys.constants import *
from winsys.exceptions import *

PyHANDLE = pywintypes.HANDLEType

class x_registry (x_winsys):
  pass
  
class x_moniker (x_registry):
  pass
  
class x_moniker_ill_formed (x_moniker):
  pass
  
class x_moniker_no_root (x_moniker):
  pass

class x_not_found (x_registry):
  pass

sep = u"\\"

WINERROR_MAP = {
  winerror.ERROR_PATH_NOT_FOUND : x_not_found,
  winerror.ERROR_FILE_NOT_FOUND : x_not_found,
  winerror.ERROR_NO_MORE_ITEMS : StopIteration,
  winerror.ERROR_ACCESS_DENIED : x_access_denied,
  winerror.ERROR_INVALID_HANDLE : x_invalid_handle,
}
wrapped = wrapper (WINERROR_MAP, x_registry)

moniker_parser = re.compile (ur"(?:\\\\([^\\]+)\\)?([^:]+)(:?)(.*)", re.UNICODE)
def parse_moniker (moniker):
  """Take a registry moniker and return the computer, root key, subkey path 
  and value. NB: neither the computer nor the registry need exist; they
  need simply to be of the right format. The slashes can be forward or
  back; they will be converted to forward slashes before the moniker
  is parsed, and the subkey path returned will use backslashes.
  
  The moniker must be of the form:
  
    [\\computer\]HKEY[\subkey path][:[value]]
  
  Valid monikers are:
    \\SVR01\HKEY_LOCAL_MACHINE\Software\Python:Version
    -> "SVR01", 0x80000002, "Software\Python", "Version"
    
    HKEY_CURRENT_USER\Software
    -> "", 0x80000001, "Software", None
    
    HKEY_CURRENT_USER\Software\Python:
    -> "", 0x80000001, "Software\Python", ""
  """
  matcher = moniker_parser.match (moniker)
  if not matcher:
    core.debug (u"parse_moniker: %s", moniker)
    raise x_moniker_ill_formed, u"Ill-formed moniker"
  computer, keypath, colon, value = matcher.groups ()
  keys = keypath.split (sep)
  
  root = path = None

  key0 = keys.pop (0)
  try:
    root = REGISTRY_HIVE[key0.upper ()]
  except KeyError:
    root = None
  
  if root is None:
    key1 = keys.pop (0)    
    try:
      root = REGISTRY_HIVE[key1.upper ()]
    except KeyError:
      root = None

  if root is None:
    raise x_moniker_no_root, u"A registry hive must be the first or second segment in moniker"
  
  path = sep.join (keys)
  
  #
  # If a value is indicated (by a colon) but none is supplied,
  # use "" to indicate that the default value is requested.
  # Otherwise use None to indicate that no value is requested
  #
  if value == u"" and not colon:
    value = None
  return computer, root, path, value

def create_moniker (computer, root, path, value=None):
  if root not in REGISTRY_HIVE:
    root = REGISTRY_HIVE.name_from_value (root)
  fullpath = sep.join ([root] + path.split (sep))
  if computer:
    moniker = ur"\\%s\%s" % (computer, fullpath)
  else:
    moniker = fullpath
  if value:
    return moniker + ":" + value
  else:
    return moniker

class Key (core._WinSysObject):

  ACCESS = {
    u"Q" : REGISTRY_ACCESS.KEY_QUERY_VALUE,
    u"D" : ACCESS.DELETE,
    u"R" : REGISTRY_ACCESS.KEY_READ,
    u"W" : REGISTRY_ACCESS.KEY_WRITE,
    u"C" : REGISTRY_ACCESS.KEY_READ | REGISTRY_ACCESS.KEY_WRITE,
    u"F" : REGISTRY_ACCESS.KEY_ALL_ACCESS,
  }
  DEFAULT_ACCESS = u"R"
  
  def __init__ (self, hKey=None, moniker=u""):
    core._WinSysObject.__init__ (self)
    utils._set (self, "hKey", hKey)
    utils._set (self, "moniker", unicode (moniker))
    utils._set (self, "name", moniker.split (sep)[-1] if moniker else "")
    
  @classmethod
  def _access (cls, access):
    try:
      return int (access)
    except ValueError:
      return reduce (operator.or_, (cls.ACCESS[a] for a in access.upper ()), 0)

  def pyobject (self, access=None):
    if self.hKey is None:
      hKey, moniker = self._from_string (self.moniker, access=self._access (access or self.DEFAULT_ACCESS))
      utils._set (self, "hKey", hKey)
      if self.hKey is None:
        raise x_not_found ("Key %s not accessible", "pyobject", 0)
      else:
        return self.hKey

    else:
      if access is None:
        return self.hKey
      else:
        return wrapped (win32api.RegOpenKeyEx, self.hKey, "", 0, self._access (access))
  
  def as_string (self):
    return self.moniker
  
  def security (self, options=security.Security.DEFAULT_OPTIONS):
    return security.Security.from_object (
      self.pyobject (ACCESS.READ_CONTROL | ACCESS.WRITE_DAC), 
      object_type=SE_OBJECT_TYPE.REGISTRY_KEY, 
      options=options
    )

  def __nonzero__ (self):
    hKey, value = self._from_string (self.moniker)
    return bool (hKey)
  
  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    if bool (self):
      output.append ("keys:\n%s" % utils.dumped_list ((key.name for key in self.keys (ignore_access_errors=True)), level))
      output.append ("values:\n%s" % utils.dumped_dict (dict ((name, repr (value)) for (name, value, type) in self.values (ignore_access_errors=True)), level))
      output.append ("security:\n%s" % utils.dumped (self.security ().dumped (level), level))
    return utils.dumped ("\n".join (output), level)
  
  def __getattr__ (self, attr):
    try:
      value, type = self.get_value (attr)
      return value
    except x_not_found:
      try:
        return self.get_key (attr)
      except x_not_found:
        raise AttributeError
    
  def __setattr__ (self, attr, value):
    self.set_value (attr, value)
    
  def values (self, ignore_access_errors=False):
    return values (self, ignore_access_errors=ignore_access_errors)
      
  def keys (self, access=DEFAULT_ACCESS, ignore_access_errors=False):
    return keys (self, ignore_access_errors=ignore_access_errors)
  
  def get_value (self, name):
    return wrapped (win32api.RegQueryValueEx, self.pyobject (), name)

  def get_key (self, name, access=DEFAULT_ACCESS):
    return self.__class__ (
      wrapped (win32api.RegOpenKeyEx, self.pyobject (), name, 0, self._access (access)),
      self.moniker+ sep + name
    )

  def set_value (self, label, value):
    def _guess_type (value):
      try:
        int (value)
      except ValueError:
        pass
      else:
        return REGISTRY_VALUE_TYPE.REG_DWORD
      if isinstance (value, list):
        return REGISTRY_VALUE_TYPE.REG_MULTI_SZ
      if unicode (value).count (u"%") % 2 == 0:
        return REGISTRY_VALUE_TYPE.REG_EXPAND_SZ
      return REGISTRY_VALUE_TYPE.REG_SZ
    
    if isinstance (value, tuple):
      value, type = value
    else:
      type = _guess_type (value)
    wrapped (win32api.RegSetValueEx, self.pyobject (), label, 0, type, value)
    
  def delete (self, *args, **kwargs):
    return delete (self, *args, **kwargs)
    
  def create (self, *args, **kwargs):
    return create (self, *args, **kwargs)
    
  def walk (self, *args, **kwargs):
    return walk (self, *args, **kwargs)
    
  def add (self, name):
    return create (self.moniker + sep + name)
  
  def parent (self, access=DEFAULT_ACCESS):
    computer, root, path, value = parse_moniker (self.moniker)
    parent_moniker = create_moniker (computer, root, sep.join (path.split (sep)[:-1]))
    pcomputer, proot, ppath, pvalue = parse_moniker (parent_moniker)
    if ppath:
      return self.from_string (parent_moniker, access)
    else:
      raise x_registry ("%s has no parent" % self.moniker)
      
  def copy (self, other):
    return copy (self, other)
  
  @classmethod
  def _from_string (cls, string, access=DEFAULT_ACCESS):
    computer, root, path, value = parse_moniker (string)
    if computer:
      hRoot = wrapped (win32api.RegConnectRegistry, computer, root)
    else:
      hRoot = root
    
    try:
      return wrapped (win32api.RegOpenKeyEx, hRoot, path, 0, cls._access (access)), value
    except (x_not_found, x_access_denied):
      return None, value
      
  @classmethod
  def from_string (cls, string, access=DEFAULT_ACCESS):
    hKey, value = cls._from_string (string, access)
    if value is None:
      return cls (hKey, string)
    else:
      return cls (hKey, string).get_value (value)

#
# Module-level convenience functions, many of them called from
# within the Key class by simply passing all parameters through.
# Most will take as the first param anything which can be converted
# to a Key, including a regpath string, a pywin32 HKEY or an
# actual Key instance.
#
def key (root, access=Key.DEFAULT_ACCESS):
  if root is None:
    return None
  elif isinstance (root, Key):
    return root
  elif isinstance (root, PyHANDLE):
    return Key (root, None)
  else:
    return Key.from_string (unicode (root), access=access)

def values (key, ignore_access_errors=False):
  try:
    hKey = key.pyobject ()
  except x_access_denied:
    if ignore_access_errors:
      raise StopIteration
    else:
      raise
      
  values = []
  i = 0
  while True:
    try:
      yield wrapped (win32api.RegEnumValue, hKey, i)
    except x_access_denied:
      if ignore_access_errors:
        pass
      else:
        raise
    i += 1

def keys (root, access=Key.DEFAULT_ACCESS, ignore_access_errors=False):
  root = key (root)
  try:
    hRoot = root.pyobject (access=Key._access (access))
  except x_access_denied:
    if ignore_access_errors:
      raise StopIteration
    else:
      raise
  
  for subname, reserved, subclass, written_at in wrapped (win32api.RegEnumKeyEx, hRoot):
    try:
      yield Key (
        wrapped (win32api.RegOpenKeyEx, hRoot, subname, 0, Key._access (access)), 
        root.moniker + sep + subname
      )
    except x_access_denied:
      if ignore_access_errors:
        continue
      else:
        raise

def copy (from_key, to_key):
  source = key (from_key)
  target = key (to_key)
  if not target:
    target.create ()

  for root, subkeys, subvalues in walk (source):
    target_root = key (target.moniker + utils.relative_to (root.moniker, source.moniker))
    for k in subkeys:
      target_key = key (target.moniker + utils.relative_to (k.moniker, source.moniker))
      target_key.create ()    
    for name, value, type in subvalues:
      target_root.set_value (name, (value, type))
      
  return key (to_key)
  
def delete (root):
  root = key (root)
  for k in root.keys ():
    k.delete ()
  win32api.RegDeleteKey (root.parent ().pyobject ("D"), root.name)

def create (root, sec=None):
  computer0, root0, path0, value0 = parse_moniker (key (root).moniker)
  
  parts = path0.split (sep)
  for i, part in enumerate (parts):
    computer, root, path, value = parse_moniker (create_moniker (computer0, root0, sep.join (parts[:i+1])))
    if computer:
      hRoot = wrapped (win32api.RegConnectRegistry, computer, root)
    else:
      hRoot = root
    security_attributes = sec.pyobject () if sec else None
    wrapped (win32api.RegCreateKeyEx, hRoot, path, Key._access (Key.DEFAULT_ACCESS), security_attributes)

def walk (root, access=Key.DEFAULT_ACCESS, ignore_access_errors=False):
  root = key (root)
  access = Key._access (access)
  yield (
    root, 
    root.keys (access=access, ignore_access_errors=ignore_access_errors), 
    root.values (ignore_access_errors=ignore_access_errors)
  )
  for subkey in root.keys (access=access, ignore_access_errors=ignore_access_errors):
    for result in walk (subkey, access, ignore_access_errors):
      yield result

if __name__ == '__main__':
  key ("HKLM/Software/python/PythonCore/%s" % ".".join (str (i) for i in sys.version_info[:2])).dump ()
  raw_input ("Press enter...")
