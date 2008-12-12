from nose.tools import *
import winerror
import win32api
import win32con
import win32security
import pywintypes
import uuid

from winsys import registry, utils

GUID = str (uuid.uuid1 ())
TEST_KEY = r"HKCU\Software\winsys"
TEST_KEY1 = r"HKCU\Software\winsys1"
TEST_KEY2 = r"HKCU\Software\winsys1\winsys2"

#
# Fixtures
#
def setup ():
  win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"Software\winsys")
  hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
  win32api.RegSetValueEx (hKey, "winsys1", None, win32con.REG_SZ, GUID)
  win32api.RegSetValueEx (hKey, "winsys2", None, win32con.REG_SZ, GUID)
  hSubkey = win32api.RegCreateKey (hKey, "winsys2")
  win32api.RegSetValueEx (hSubkey, "winsys2", None, win32con.REG_SZ, GUID)
  
def teardown ():
  hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.READ_CONTROL|win32con.WRITE_DAC)
  dacl = win32security.ACL ()
  sid, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())
  dacl.AddAccessAllowedAce (win32security.ACL_REVISION_DS, win32con.KEY_ALL_ACCESS, sid)
  win32security.SetSecurityInfo (
    hKey, win32security.SE_REGISTRY_KEY, 
    win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION, 
    None, None, dacl, None
  )
  remove_key (win32con.HKEY_CURRENT_USER, r"Software\winsys")
  
#
# Utility functions
#
def remove_key (root, key):
  hkey = win32api.RegOpenKey (root, key)
  for name, reserved, klass, last_written in win32api.RegEnumKeyEx (hkey):
    remove_key (hkey, name)
  win32api.RegDeleteKey (root, key)

def remove_access (path=r"software\winsys"):
  hKey = win32api.RegOpenKeyEx (
    win32con.HKEY_CURRENT_USER, path, 0, 
    win32con.READ_CONTROL|win32con.WRITE_DAC
  )
  dacl = win32security.ACL ()
  win32security.SetSecurityInfo (
    hKey, win32security.SE_REGISTRY_KEY, 
    win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION, 
    None, None, dacl, None
  )
  
def restore_access (path=r"software\winsys"):
  hKey = win32api.RegOpenKeyEx (
    win32con.HKEY_CURRENT_USER, path,
    0, 
    win32con.READ_CONTROL|win32con.WRITE_DAC
  )
  win32security.SetSecurityInfo (
    hKey, win32security.SE_REGISTRY_KEY, 
    win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION, 
    None, None, None, None
  )
  
def keys_are_equal (key0, key1):
  return \
    list ((utils.relative_to (key.moniker, key0), list (values)) for key, subkeys, values in registry.walk (key0)) == \
    list ((utils.relative_to (key.moniker, key1), list (values)) for key, subkeys, values in registry.walk (key1))

def key0_subset_of_key1 (key0, key1):
  s0 = set ((utils.relative_to (key.moniker, key0), frozenset (values)) for key, subkeys, values in registry.walk (key0))
  s1 = set ((utils.relative_to (key.moniker, key1), frozenset (values)) for key, subkeys, values in registry.walk (key1))
  return s0 < s1

#
# TESTS
#

#
# test disabled until I can figure out a way to make it fail!
#
#~ def test_moniker_ill_formed ():
  #~ assert_raises (registry.x_moniker_ill_formed, registry.parse_moniker, r"IN\VA:LID\MONI\KER")
  
@raises (registry.x_moniker_no_root)
def test_moniker_computer_only ():
  registry.parse_moniker (r"\\computer")
    
@raises (registry.x_moniker_no_root)
def test_moniker_invalid_root ():
  registry.parse_moniker (r"<nonsense>")

def test_moniker_slash_and_root ():
  assert_equals (registry.parse_moniker (r"\HKLM"), (None, win32con.HKEY_LOCAL_MACHINE, "", None))
    
def test_moniker_root_only ():
  assert_equals (registry.parse_moniker ("HKLM"), (None, win32con.HKEY_LOCAL_MACHINE, "", None))
    
def test_moniker_computer_and_root ():
  assert_equals (registry.parse_moniker (r"\\COMPUTER\HKLM"), ("COMPUTER", win32con.HKEY_LOCAL_MACHINE, "", None))

def test_moniker_root_and_body ():
  assert_equals (registry.parse_moniker (r"HKLM\Software\Microsoft"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", None))

def test_moniker_computer_root_and_body ():
  assert_equals (registry.parse_moniker (r"\\COMPUTER\HKLM\Software\Microsoft"), ("COMPUTER", win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", None))

@raises (registry.x_moniker_no_root)
def test_moniker_body_only ():
  registry.parse_moniker (r"Software\Microsoft")

def test_moniker_default_value ():
  assert_equals (registry.parse_moniker (r"HKLM\Software\Microsoft:"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", ""))

def test_moniker_value ():
  assert_equals (registry.parse_moniker (r"HKLM\Software\Microsoft:value"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", "value"))

def test_moniker_create ():
  parts = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", "VALUE"
  assert_equals (registry.parse_moniker (registry.create_moniker (*parts)), parts)

def test_moniker_create_named_root ():
  parts = "COMPUTER", "HKLM", "PATH", "VALUE"
  result = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", "VALUE"
  assert_equals (registry.parse_moniker (registry.create_moniker (*parts)), result)

def test_moniker_create ():
  parts = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", None
  assert_equals (registry.parse_moniker (registry.create_moniker (*parts)), parts)

def test_registry_None ():
  assert registry.registry (None) is None
  
def test_registry_Key ():
  key = registry.registry ("HKLM")
  assert registry.registry (key) is key

def test_registry_string ():
  assert registry.registry (TEST_KEY).winsys1 == GUID

@raises (registry.x_registry)
def test_registry_other ():
  hKey = win32api.RegOpenKey (win32con.HKEY_LOCAL_MACHINE, "Software")
  registry.registry (hKey)
  
def test_values ():
  values = registry.values (TEST_KEY)
  assert values.next () == ('winsys1', GUID, win32con.REG_SZ)
  assert values.next () == ('winsys2', GUID, win32con.REG_SZ)

@raises (registry.x_access_denied)
def test_values_access_denied ():
  key = registry.registry (TEST_KEY, win32con.KEY_ENUMERATE_SUB_KEYS)
  registry.values (key).next ()

def test_values_ignore_access_denied ():
  key = registry.registry (TEST_KEY, win32con.KEY_ENUMERATE_SUB_KEYS)
  values = registry.values (key, ignore_access_errors=True)
  assert list (values) == []

def test_keys ():
  keys = registry.keys (TEST_KEY)
  assert keys.next () == registry.registry (TEST_KEY + r"\winsys2")

@raises (registry.x_access_denied)
def test_keys_access_denied ():
  key = registry.registry (TEST_KEY, win32con.KEY_NOTIFY)
  keys = registry.keys (key, ignore_access_errors=False)
  keys.next ()

def test_keys_ignore_access_denied ():
  key = registry.registry (TEST_KEY, win32con.KEY_NOTIFY)
  keys = registry.keys (key, ignore_access_errors=True)
  assert list (keys) == []

def test_copy_does_not_exist ():
  key0 = TEST_KEY
  key1 = TEST_KEY1
  registry.copy (key0, key1)
  try:
    assert keys_are_equal (key0, key1)
  finally:
    registry.delete (key1)

def test_copy_exists_empty ():
  key0 = registry.registry (TEST_KEY)
  key1 = registry.registry (TEST_KEY1)
  assert not bool (key1)
  key1.create ()
  assert bool (key1)
  registry.copy (key0, key1)
  try:
    assert keys_are_equal (key0, key1)
  finally:
    key1.delete ()

def test_copy_exists_not_empty_keys ():
  key0 = registry.registry (TEST_KEY)
  key1 = registry.registry (TEST_KEY1)
  assert not bool (key1)
  key1.create ()
  assert bool (key1)
  try:
    key1.add ("winsys4")
    registry.copy (key0, key1)
    assert key0_subset_of_key1 (key0, key1)
  finally:
    key1.delete ()

def test_copy_exists_not_empty_values ():
  key0 = registry.registry (TEST_KEY)
  key1 = registry.registry (TEST_KEY1)
  assert not bool (key1)
  key1.create ()
  assert bool (key1)
  try:
    key1.winsys4 = GUID
    registry.copy (key0, key1)
    assert set (set (key1.flat ()) - set (key0.flat ())) == \
      set ([("winsys4", GUID, win32con.REG_SZ), key1, key1 + "winsys2"])
  finally:
    key1.delete ()

def test_create_does_not_exist ():
  key1 = registry.registry (TEST_KEY1)
  assert not bool (key1)
  registry.create (key1)
  try:
    assert bool (key1)
  finally:
    key1.delete ()

def test_create_does_not_exist_deep ():
  key1 = registry.registry (TEST_KEY1)
  key2 = registry.registry (TEST_KEY2)
  assert not bool (key1)
  assert not bool (key2)
  registry.create (key2)
  try:
    assert bool (key1)
    assert bool (key2)
  finally:
    key1.delete ()

def test_create_does_exist ():
  key = registry.registry (TEST_KEY)
  assert bool (key)
  registry.create (key)
  assert bool (key)

def test_walk ():
  walker = registry.walk (TEST_KEY)
  key, subkeys, values = walker.next ()
  assert key == registry.registry (TEST_KEY)
  assert list (values) == [("winsys1", GUID, win32con.REG_SZ), ("winsys2", GUID, win32con.REG_SZ)]  
  key, subkeys, values = walker.next ()
  assert key == registry.registry (TEST_KEY) + "winsys2"
  assert list (values) == [("winsys2", GUID, win32con.REG_SZ)]

@raises (registry.x_access_denied)
def test_walk_access_denied ():
  key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
  walker = registry.walk (key)
  key, keys, values = walker.next ()
  list (keys)

def test_walk_ignore_access_denied ():
  key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
  walker = registry.walk (key, ignore_access_errors=True)
  key, keys, values = walker.next ()
  list (keys) == [key + "winsys2"]

def test_flat ():
  key = registry.registry (TEST_KEY)
  assert list (registry.flat (key)) == [
    key, 
    ("winsys1", GUID, win32con.REG_SZ), 
    ("winsys2", GUID, win32con.REG_SZ), 
    key + "winsys2", 
    ("winsys2", GUID, win32con.REG_SZ)
  ]

@raises (registry.x_access_denied)
def test_flat_access_denied ():
  key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
  list (registry.flat (key))

def test_flat_ignore_access_denied ():
  remove_access (r"software\winsys\winsys2")
  try:
    key = registry.registry (TEST_KEY)
    f = registry.flat (key, ignore_access_errors=True)
    print f.next ()
    print f.next ()
    assert list (registry.flat (key, ignore_access_errors=True)) == [
      key, 
      ("winsys1", GUID, win32con.REG_SZ), 
      ("winsys2", GUID, win32con.REG_SZ),
      key + "winsys2"
    ]
  finally:
    restore_access (r"software\winsys\winsys2")
    
def test_parent ():
  assert registry.parent (TEST_KEY + r"\winsys2") == registry.registry (TEST_KEY)

def test_identical_functions ():
  functions = "values keys delete create walk flat copy parent".split ()
  for function in functions:
    assert getattr (registry, function).func_code is getattr (registry.Registry, function).func_code

def test_Registry_init ():
  key = registry.Registry (TEST_KEY, access=win32con.KEY_ALL_ACCESS)
  assert key.moniker == TEST_KEY
  assert key.name == "winsys"
  assert key.access == win32con.KEY_ALL_ACCESS
  print key.id
  assert key.id == registry.parse_moniker (TEST_KEY.lower ())

def test_Registry_init_access ():
  for k, v in registry.Registry.ACCESS.items ():
    assert registry.registry (TEST_KEY, k).access == v

def test_Registry_access ():
  access = registry.Registry._access
  assert access (None) is None
  assert access (1) == 1
  for k, v in registry.Registry.ACCESS.items ():
    assert registry.registry (TEST_KEY, k).access == v

def test_Registry_eq ():
  assert registry.registry (TEST_KEY.upper (), access="R") == registry.registry (TEST_KEY.lower (), access="R")  

def test_Registry_neq ():
  assert registry.registry (TEST_KEY.upper (), access="R") != registry.registry (TEST_KEY.lower (), access="W")

def test_Registry_add ():
  assert registry.registry (TEST_KEY) + "test" == registry.registry (TEST_KEY + registry.sep + "test")
  
def test_Registry_pyobject ():
  assert isinstance (registry.registry (TEST_KEY).pyobject (), pywintypes.HANDLEType)

@raises (registry.x_not_found)
def test_Registry_pyobject_not_exists ():
  assert not bool (registry.registry (TEST_KEY + "xxx"))
  registry.registry (TEST_KEY + "xxx").pyobject ()

def test_Registry_as_string ():
  key = registry.registry (TEST_KEY)
  assert key.as_string () == key.moniker

def test_Registry_security ():
  security_information = win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
  key = registry.registry (TEST_KEY)
  security = key.security (security_information)
  sd = win32security.GetSecurityInfo (
    win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), 
    win32security.SE_REGISTRY_KEY,
    security_information
  )
  assert \
    security.as_string () == \
      win32security.ConvertSecurityDescriptorToStringSecurityDescriptor (
        sd,
        win32security.SDDL_REVISION_1, 
        security_information
      )

def test_Registry_nonzero_exists ():
  win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"Software\winsys1")
  try:
    assert bool (registry.registry (TEST_KEY1))
  finally:
    win32api.RegDeleteKey (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"Software"), "winsys1")

def test_Registry_nonzero_not_exists ():
  try:
    win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"Software\winsys1")
  except win32api.error, (errno, errctx, errmsg):
    if errno != winerror.ERROR_FILE_NOT_FOUND:
      raise
  else:
    raise RuntimeError ("Key exists but should not")
  
  assert not bool (registry.registry (TEST_KEY1))

def test_Registry_dumped ():
  #
  # Just test it doesn't fall over
  #
  dump = registry.registry ("HKLM").dumped ()

def test_Registry_get_value ():
  assert \
    registry.registry (TEST_KEY).get_value ("winsys1") == \
    win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys1")
    
def test_Registry_get_key ():
  assert \
    registry.registry (TEST_KEY).get_key ("winsys1") == \
    registry.registry (TEST_KEY + r"\winsys1")
    
def test_Registry_getattr_value ():
  value, type = win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys1")
  assert registry.registry (TEST_KEY).winsys1 == value
    
def test_Registry_getattr_value_shadows_key ():
  value, type = win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys2")
  assert registry.registry (TEST_KEY).winsys2 == value
    
def test_Registry_getattr_key ():
  win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"software\winsys\winsys3")
  try:
    assert registry.registry (TEST_KEY).winsys3 == registry.registry (TEST_KEY).get_key ("winsys3")
  finally:
    win32api.RegDeleteKey (win32con.HKEY_CURRENT_USER, r"Software\winsys\winsys3")

def test_Registry_set_value_type ():
  registry.registry (TEST_KEY).set_value ("winsys4", ("abc", win32con.REG_BINARY))
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("abc", win32con.REG_BINARY)

def test_Registry_set_value_int ():
  registry.registry (TEST_KEY).set_value ("winsys4", 1)
  assert registry.registry (TEST_KEY).get_value ("winsys4") == (1, win32con.REG_DWORD)

def test_Registry_set_value_multi ():
  registry.registry (TEST_KEY).set_value ("winsys4", ['a', 'b', 'c'])
  assert registry.registry (TEST_KEY).get_value ("winsys4") == (['a', 'b', 'c'], win32con.REG_MULTI_SZ)

def test_Registry_set_value_expand_even_percent ():
  registry.registry (TEST_KEY).set_value ("winsys4", "%TEMP%")
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("%TEMP%", win32con.REG_EXPAND_SZ)

def test_Registry_set_value_expand_odd_percent ():
  registry.registry (TEST_KEY).set_value ("winsys4", "50%")
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("50%", win32con.REG_SZ)

def test_Registry_set_value_empty_string ():
  registry.registry (TEST_KEY).set_value ("winsys4", "")
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("", win32con.REG_SZ)

def test_Registry_set_value_non_empty_string ():
  registry.registry (TEST_KEY).set_value ("winsys4", "winsys")
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("winsys", win32con.REG_SZ)

def test_Registry_set_value_none ():
  registry.registry (TEST_KEY).set_value ("winsys4", None)
  assert registry.registry (TEST_KEY).get_value ("winsys4") == ("", win32con.REG_SZ)

def test_Registry_set_value_default ():
  registry.registry (TEST_KEY).set_value ("", "test")
  assert registry.registry (TEST_KEY).get_value ("") == ("test", win32con.REG_SZ)

def test_Registry_add ():
  key0 = registry.registry (TEST_KEY)
  new_key = key0.add ("winsys1")
  assert new_key == key0 + "winsys1"

def test_Registry_from_string ():
  key = registry.Registry.from_string (TEST_KEY)
  assert key.moniker == TEST_KEY
  assert key.access == registry.Registry._access (registry.Registry.DEFAULT_ACCESS)
  assert key.id == registry.parse_moniker (TEST_KEY.lower ())

def test_Registry_from_string_value ():
  assert registry.Registry.from_string (TEST_KEY + ":winsys1") == registry.Registry.from_string (TEST_KEY).get_value ("winsys1")

if __name__ == '__main__':
  import nose
  nose.runmodule (exit=False) 
  raw_input ("Press enter...")
