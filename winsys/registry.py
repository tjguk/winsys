# -*- coding: iso-8859-1 -*-
"""
Introduction
------------
The registry consists of a series of roots from each of which descends
a tree of keys and values. Each key has an anonymous (default) value
and optionally a set of named values, each of which has a particular
type (string, number etc.).

.. _registry_monikers:

Monikers
~~~~~~~~
For convenience in accessing registry keys and values, the module
implements the idea of a registry moniker which has the form:
:const:`[\\\\computer\\]HKEY[\\subkey path][:[value]]`. For example::

  from winsys import registry

  #
  # The value of the Version item in the HKLM\Software\Python key on SVR01
  #
  registry.registry (r"\\SVR01\HKEY_LOCAL_MACHINE\Software\Python:Version")

  #
  # The Control Panel\Desktop key in HKEY_CURRENT_USER on the current machine
  #
  registry.registry (r"HKCU\Control Panel\Desktop")

The key function here is :func:`registry` which is a factory 
returning an instance of the :class:`Registry` class which contains
most of the useful functionality in the module. However, the same
functionality is replicated at module level in many cases for
convenience.

So the :meth:`Registry.delete` method, for example, is equivalent to
the :func:`delete` function at module level. Likewise, :func:`copy`
hands off to the :meth:`Registry.copy` method. This makes it convenient
to perform actions which are more naturally expressed in terms of a
pair of registry monikers.
"""
import os, sys
import operator
import re

import winerror
import win32api
import win32con
import pywintypes

from winsys import constants, core, utils, security
from winsys.exceptions import *

REGISTRY_HIVE = constants.Constants.from_list ([
  u"HKEY_CLASSES_ROOT",
  u"HKEY_CURRENT_CONFIG",
  u"HKEY_CURRENT_USER",
  u"HKEY_DYN_DATA",
  u"HKEY_LOCAL_MACHINE",
  u"HKEY_PERFORMANCE_DATA",
  u"HKEY_PERFORMANCE_NLSTEXT",
  u"HKEY_PERFORMANCE_TEXT",
  u"HKEY_USERS",
], namespace=win32con)
REGISTRY_HIVE.update (dict (
  HKLM = REGISTRY_HIVE.HKEY_LOCAL_MACHINE,
  HKCU = REGISTRY_HIVE.HKEY_CURRENT_USER,
  HKCR = REGISTRY_HIVE.HKEY_CLASSES_ROOT,
  HKU = REGISTRY_HIVE.HKEY_USERS
))
REGISTRY_ACCESS = constants.Constants.from_list ([
  u"KEY_ALL_ACCESS",
  u"KEY_CREATE_LINK",
  u"KEY_CREATE_SUB_KEY",
  u"KEY_ENUMERATE_SUB_KEYS",
  u"KEY_EXECUTE",
  u"KEY_NOTIFY",
  u"KEY_QUERY_VALUE",
  u"KEY_READ",
  u"KEY_SET_VALUE",
  u"KEY_WOW64_32KEY",
  u"KEY_WOW64_64KEY",
  u"KEY_WRITE",
], namespace=win32con)
#
#: Types of data allowed in registry
#
REGISTRY_VALUE_TYPE = constants.Constants.from_list ([
  u"REG_BINARY",
  u"REG_DWORD",
  u"REG_DWORD_LITTLE_ENDIAN",
  u"REG_DWORD_BIG_ENDIAN",
  u"REG_EXPAND_SZ",
  u"REG_LINK",
  u"REG_MULTI_SZ",
  u"REG_NONE",
  u"REG_QWORD",
  u"REG_QWORD_LITTLE_ENDIAN",
  u"REG_SZ",
], namespace=win32con)

PyHANDLE = pywintypes.HANDLEType

class x_registry (x_winsys):
  "Base exception for all registry exceptions"
  
class x_moniker (x_registry):
  "Base exception for problems with monikers"
  
class x_moniker_ill_formed (x_moniker):
  "Raised when a moniker does not match the correct format"
  
class x_moniker_no_root (x_moniker):
  "Raised when a moniker has no Hive in the first or second position"

sep = u"\\"

WINERROR_MAP = {
  winerror.ERROR_PATH_NOT_FOUND : x_not_found,
  winerror.ERROR_FILE_NOT_FOUND : x_not_found,
  winerror.ERROR_NO_MORE_ITEMS : StopIteration,
  winerror.ERROR_ACCESS_DENIED : x_access_denied,
  winerror.ERROR_INVALID_HANDLE : x_invalid_handle,
}
wrapped = wrapper (WINERROR_MAP, x_registry)

moniker_parser = re.compile (ur"(?:\\\\([^\\]+)\\)?(.*)$", re.UNICODE)
def _parse_moniker (moniker):
  """Take a registry moniker and return the computer, root key, and subkey path. 
  NB: neither the computer nor the registry need exist; they
  need simply to be of the right format. The slashes can be forward or
  back; they will be converted to forward slashes before the moniker
  is parsed, and the subkey path returned will use backslashes.
  
  The moniker must be of the form:
  
    [\\computer\]HKEY[\subkey path]
  
  Valid monikers are:
    \\SVR01\HKEY_LOCAL_MACHINE\Software\Python
    -> "SVR01", 0x80000002, "Software\Python"
    
    HKEY_CURRENT_USER\Software
    -> "", 0x80000001, "Software"
    
    HKEY_CURRENT_USER\Software\Python:
    -> "", 0x80000001, "Software\Python"
  """
  matcher = moniker_parser.match (moniker)
  if not matcher:
    raise x_moniker_ill_formed (core.UNSET, u"_parse_moniker", u"Ill-formed moniker: %s" % moniker)
  computer, keypath = matcher.groups ()
  keys = keypath.split (sep)
  
  root = path = None

  key0 = keys.pop (0)
  try:
    root = REGISTRY_HIVE[key0.upper ()]
  except KeyError:
    root = None
  
  if root is None and keys:
    key1 = keys.pop (0)
    try:
      root = REGISTRY_HIVE[key1.upper ()]
    except KeyError:
      root = None

  if root is None:
    raise x_moniker_no_root (core.UNSET, u"_parse_moniker", u"A registry hive must be the first or second segment in moniker")
  
  path = sep.join (keys)
  
  return computer, root, path, None

def create_moniker (computer, root, path, value=None):
  """Return a valid registry moniker from component parts. Computer
  is optional but root and path must be specified.
  
  :param computer: (optional) name of a remote computer or "."
  :param root: name or value from REGISTRY_HIVE
  :param path: backslash-separated registry path
  :param value: (OBSOLETE) name of a value on that path. An empty string refers to the default value.
  :returns: a valid moniker string
  """
  if root not in REGISTRY_HIVE:
    root = REGISTRY_HIVE.name_from_value (root)
  fullpath = sep.join ([root] + path.split (sep))
  if computer:
    moniker = ur"\\%s\%s" % (computer, fullpath)
  else:
    moniker = fullpath
  return moniker

class Registry (core._WinSysObject):
  """  
  Represent a registry key (including one of the roots) giving
  access to its subkeys and values as well as its security and walking
  its subtrees. The key is True if it exists, False otherwise.
  
  Adding a key name to this registry key will return in a fresh Registry
  instance for that subkey. Reading an attribute of this key will return
  a value of that name if one exists, otherwise a key if one exists. Writing
  an attribute will always write a value, guessing the type.
  
  When access rights are supplied to any function, they can either be an 
  integer representing a bitmask, or one or more letters corresponding to 
  the :attr:`ACCESS` mapping. The default access is "F" indicating 
  Full Control.
  """

  ACCESS = {
    u"Q" : REGISTRY_ACCESS.KEY_QUERY_VALUE,
    u"D" : constants.ACCESS.DELETE,
    u"R" : REGISTRY_ACCESS.KEY_READ,
    u"W" : REGISTRY_ACCESS.KEY_WRITE,
    u"C" : REGISTRY_ACCESS.KEY_READ | REGISTRY_ACCESS.KEY_WRITE,
    u"F" : REGISTRY_ACCESS.KEY_ALL_ACCESS,
    u"S" : constants.ACCESS.READ_CONTROL | constants.ACCESS.WRITE_DAC,
  }
  """Mapping between characters and access rights:
  
  * Q - Query
  * D - Delete
  * R - Read
  * W - Write
  * C - Change (R|W)
  * F - Full Control
  * S - Security
  """
  DEFAULT_ACCESS = u"F"
  
  def __init__ (self, moniker, access=DEFAULT_ACCESS):
    core._WinSysObject.__init__ (self)
    utils._set (self, "hKey", None)
    utils._set (self, "moniker", unicode (moniker))
    utils._set (self, "id", _parse_moniker (self.moniker.lower ()))
    utils._set (self, "access", self._access (access))
    utils._set (self, "name", moniker.split (sep)[-1] if moniker else "")
    
  @classmethod
  def _access (cls, access):
    """Conversion function which returns an integer representing a security access
    bit pattern. Uses the class's ACCESS map to translate letters to integers.
    """
    if access is None:
      return None      
    try:
      return int (access)
    except ValueError:
      return reduce (operator.or_, (cls.ACCESS[a] for a in access.upper ()), 0)

  def __eq__ (self, other):
    return self.id == other.id and self.access == other.access
    
  def __add__ (self, path):
    """Allow a key to be added to an existing moniker
    """
    return self.__class__ (self.moniker + sep + path)
  
  def pyobject (self):
    """Lazily return an internal registry key handle according to the instance's
    access requirements.
    
    :raises: :exc:`x_not_found` if the registry path the key refers to does not exist
    """
    if self.hKey is None:
      hKey, moniker = self._from_string (self.moniker, access=self.access)
      utils._set (self, "hKey", hKey)
      if self.hKey is None:
        raise x_not_found (core.UNSET, u"Registry.pyobject", u"Registry path %s not found" % moniker)
    return self.hKey
  
  def as_string (self):
    return self.moniker
  
  def security (self, options=security.Security.DEFAULT_OPTIONS):
    """For a security request, hand off to the :meth:`~security.Security.from_object` method
    of the :class:`security.Security` object, specifying a registry key as the object type.
    """
    return security.Security.from_object (
      self.pyobject (), 
      object_type=security.SE_OBJECT_TYPE.REGISTRY_KEY, 
      options=options
    )

  def __nonzero__ (self):
    """Determine whether the registry key exists or not.
    """
    hKey, value = self._from_string (self.moniker)
    return bool (hKey)
  
  def dumped (self, level=0):
    output = []
    output.append (self.as_string ())
    output.append (u"access: %s" % self.access)
    if bool (self):
      output.append (u"keys:\n%s" % utils.dumped_list ((key.name for key in self.keys (ignore_access_errors=True)), level))
      output.append (u"values:\n%s" % utils.dumped_dict (dict ((name or u"(Default)", repr (value)) for (name, value, type) in self.values (ignore_access_errors=True)), level))
      output.append (u"security:\n%s" % utils.dumped (self.security ().dumped (level), level))
    return utils.dumped ("\n".join (output), level)
  
  def __getattr__ (self, attr):
    """Allow attribute access (key.value) by trying for a value
    first and then falling back to a key and finally raising
    AttributeError
    """
    try:
      value, type = self.get_value (attr)
      return value
    except x_not_found:
      try:
        return self.get_key (attr)
      except x_not_found:
        raise AttributeError
  __getitem__ = __getattr__

  def __setattr__ (self, attr, value):
    """Allow attribute assignment by assigning a value.
    """
    self.set_value (attr, value)
  __setitem__ = __setattr__
    
  def get_value (self, name):
    """Return the key's value corresponding to name
    """
    return wrapped (win32api.RegQueryValueEx, self.pyobject (), name)

  def get_key (self, name):
    """Return a Registry instance corresponding to the key's subkey name
    """
    return self + name

  def set_value (self, label, value):
    """Attempt to set one of the key's named values. value can
    be either a 2-tuple of (value, type) in which case the type
    is passed straight through to the underlying API; or a simple
    value, in which a guess is made at the datatype as follows:
    
    * If the value is an int, use DWORD
    * If the value is a list, use MULTI_SZ
    * If the value has an even number of percent signs, use EXPAND_SZ
    * Otherwise, use REG_SZ
    
    This is a very naive approach, and will falter if, for example,
    a string is passed which can be converted into a number, or a string
    with 2 percent signs which don't refer to an env var.
    """
    def _guess_type (value):
      try:
        int (value)
      except (ValueError, TypeError):
        pass
      else:
        return REGISTRY_VALUE_TYPE.REG_DWORD
      if isinstance (value, list):
        return REGISTRY_VALUE_TYPE.REG_MULTI_SZ
      value = unicode (value)
      if u"%" in value and value.count (u"%") % 2 == 0:
        return REGISTRY_VALUE_TYPE.REG_EXPAND_SZ
      return REGISTRY_VALUE_TYPE.REG_SZ
    
    if isinstance (value, tuple):
      value, type = value
    else:
      type = _guess_type (value)
    wrapped (win32api.RegSetValueEx, self.pyobject (), label, 0, type, value)
    
  def add (self, name, sec=None):
    """Create and return a subkey of this key with the name name.
    Hands off params to :meth:`create`.
    """
    return create (self + name, sec=sec)
  
  @classmethod
  def _from_string (cls, string, access=DEFAULT_ACCESS):
    """Treat the string param as a moniker and return the corresponding
    registry key and value name.
    """
    computer, root, path, value = _parse_moniker (string)
    if computer:
      hRoot = wrapped (win32api.RegConnectRegistry, computer, root)
    else:
      hRoot = root
    
    try:
      return wrapped (win32api.RegOpenKeyEx, hRoot, path, 0, cls._access (access)), value
    except x_not_found:
      return None, value
      
  @classmethod
  def from_string (cls, string, access=DEFAULT_ACCESS):
    """Treat the string param as a moniker return either a key
    or a value.
    """
    hKey, value = cls._from_string (string, access)
    if value is None:
      return cls (string, access)
    else:
      return cls (string, access).get_value (value)

def registry (root, access=Registry.DEFAULT_ACCESS):
  """Factory function for the Registry class.
  
  :param root: any of None, a Registry instance, or a moniker string
  :param access: an integer bitmask or an :data:`Registry.ACCESS` string  
  """
  if root is None:
    return None
  elif isinstance (root, Registry):
    return root
  elif isinstance (root, basestring):
    return Registry.from_string (root, access=access)
  else:
    raise x_registry (core.UNSET, u"registry", u"root must be None, an existing key or a moniker")

def values (root, ignore_access_errors=False):
  """Yield the values of a registry key as (name, value, type)
  
  :param root: anything accepted by :func:`registry`
  :param ignore_access_errors: if True, will keep on iterating even if access denied
  """
  root = registry (root)
  try:
    hKey = root.pyobject ()
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
        raise StopIteration
      else:
        raise
    i += 1

def keys (root, ignore_access_errors=False):
  """Yield the subkeys of a registry key as Registry instances
  
  :param root: anything accepted by :func:`registry`
  :param ignore_access_errors: if True, will keep on iterating even if access denied
  """
  root = registry (root)
  try:
    hRoot = root.pyobject ()
  except x_access_denied:
    if ignore_access_errors:
      raise StopIteration
    else:
      raise
  
  try:
    for subname, reserved, subclass, written_at in wrapped (win32api.RegEnumKeyExW, hRoot):
      yield Registry (root.moniker + sep + subname)
  except x_access_denied:
    if ignore_access_errors:
      raise StopIteration
    else:
      raise

def copy (from_key, to_key):
  """Copy one registry key to another, returning the target. If the
  target doesn't already exist it will be created.
  
  :param from_key: anything accepted by :func:`registry`
  :param to_key: anything accepted by :func:`registry`
  :returns: a :class:`Registry` instance referring to to_key
  """
  source = registry (from_key)
  target = registry (to_key)
  if not target:
    target.create ()

  for root, subkeys, subvalues in walk (source):
    target_root = registry (target.moniker + utils.relative_to (root.moniker, source.moniker))
    for k in subkeys:
      target_key = registry (target.moniker + utils.relative_to (k.moniker, source.moniker))
      target_key.create ()    
    for name, value, type in subvalues:
      target_root.set_value (name, (value, type))
      
  return registry (to_key)
  
def delete (root):
  """Delete a registry key and all its subkeys
  
  :param root: anything accepted by :func:`registry`
  """
  root = registry (root)
  for k in root.keys ():
    k.delete ()
  win32api.RegDeleteKey (root.parent ().pyobject (), root.name)

def create (root, sec=None):
  """Create a key and apply specific security to it, returning the
  key created
  
  :param root: anything accepted by :func:`registry`
  :param sec: a :class:`security.Security` instance or None
  :returns: a :class:`Registry` instance corresponding to root
  """
  key = registry (root)
  computer0, root0, path0, value0 = _parse_moniker (key.moniker)
  
  parts = path0.split (sep)
  for i, part in enumerate (parts):
    computer, root, path, value = _parse_moniker (create_moniker (computer0, root0, sep.join (parts[:i+1])))
    if computer:
      hRoot = wrapped (win32api.RegConnectRegistry, computer, root)
    else:
      hRoot = root
    security_attributes = sec.pyobject () if sec else None
    wrapped (win32api.RegCreateKeyEx, hRoot, path, Registry._access (Registry.DEFAULT_ACCESS), security_attributes)
  
  return key

def walk (root, ignore_access_errors=False):
  """Mimic the os.walk functionality for the registry, starting at root and
  yielding (key, subkeys, values) for each key visited.
  
  :param root: anything accepted by :func:`registry`
  :param ignore_access_errors: if True, will keep on iterating even if access denied
  """
  root = registry (root)
  yield (
    root, 
    root.keys (ignore_access_errors=ignore_access_errors), 
    root.values (ignore_access_errors=ignore_access_errors)
  )
  for subkey in root.keys (ignore_access_errors=ignore_access_errors):
    for result in walk (subkey, ignore_access_errors=ignore_access_errors):
      yield result

def flat (root, ignore_access_errors=False):
  """Yield a flattened version the tree rooted at root.
  
  :param root: anything accepted by :func:`registry`
  :param ignore_access_errors: if True, will keep on iterating even if access denied
  """
  for key, subkeys, values in walk (root, ignore_access_errors=ignore_access_errors):
    yield key
    for value in values:
      yield value

def parent (key):
  """Return a registry key's parent key if it exists
  
  :param key: anything accepted by :func:`registry`
  """
  key = registry (key)
  computer, root, path, value = _parse_moniker (key.moniker)
  parent_moniker = create_moniker (computer, root, sep.join (path.split (sep)[:-1]))
  pcomputer, proot, ppath, pvalue = _parse_moniker (parent_moniker)
  if ppath:
    return registry (parent_moniker, key.access)
  else:
    raise x_registry (core.UNSET, u"parent", u"%s has no parent" % key.moniker)
      
Registry.values = values
Registry.keys = keys
Registry.delete = delete
Registry.create = create
Registry.walk = walk
Registry.flat = flat
Registry.copy = copy
Registry.parent = parent
