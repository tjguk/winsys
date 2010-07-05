import sys
import pprint
print = pprint.pprint
import unittest
import uuid

import winerror
import win32api
import win32con
import win32security
import pywintypes

from winsys import registry, utils

GUID = str (uuid.uuid1 ())
TEST_KEY = r"HKEY_CURRENT_USER\Software\winsys"
TEST_KEY1 = r"HKEY_CURRENT_USER\Software\winsys1"
TEST_KEY2 = r"HKEY_CURRENT_USER\Software\winsys1\winsys2"

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

class TestRegistry (unittest.TestCase):

  #
  # Fixtures
  #
  def setUp (self):
    hwinsys = win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"Software\winsys")
    hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
    win32api.RegSetValueEx (hKey, "winsys1", None, win32con.REG_SZ, GUID)
    win32api.RegSetValueEx (hKey, "winsys1", "value", win32con.REG_SZ, GUID)
    win32api.RegSetValueEx (hKey, "winsys2", None, win32con.REG_SZ, GUID)
    hSubkey = win32api.RegCreateKey (hKey, "winsys2")
    win32api.RegSetValueEx (hSubkey, "winsys2", None, win32con.REG_SZ, GUID)
    hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
    hSubkey = win32api.RegCreateKey (hKey, "win:sys3")
    win32api.RegSetValueEx (hSubkey, "winsys3", None, win32con.REG_SZ, GUID)
    self.setup_set_value ()

  def tearDown (self):
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
  # Fixtures
  #
  #~ def setup_key_with_colon ():
    #~ hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
    #~ hSubkey = win32api.RegCreateKey (hKey, "win:sys3")
    #~ win32api.RegSetValueEx (hSubkey, "winsys3", None, win32con.REG_SZ, GUID)

  #~ def teardown_key_with_colon ():
    #~ hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
    #~ win32api.RegDeleteKey (hKey, "win:sys3")

  #
  # TESTS
  #

  #
  # test disabled until I can figure out a way to make it fail!
  #
  #~ def test_moniker_ill_formed ():
    #~ assert_raises (registry.x_moniker_ill_formed, registry._parse_moniker, r"IN\VA:LID\MONI\KER")

  def test_moniker_computer_only (self):
    with self.assertRaises (registry.x_moniker_no_root):
      registry._parse_moniker (r"\\computer")

  def test_moniker_invalid_root (self):
    with self.assertRaises (registry.x_moniker_no_root):
      registry._parse_moniker (r"<nonsense>")

  def test_moniker_slash_and_root (self):
    self.assertEquals (registry._parse_moniker (r"\HKLM"), (None, win32con.HKEY_LOCAL_MACHINE, "", None))

  def test_moniker_root_only (self):
    self.assertEquals (registry._parse_moniker ("HKLM"), (None, win32con.HKEY_LOCAL_MACHINE, "", None))

  def test_moniker_computer_and_root (self):
    self.assertEquals (registry._parse_moniker (r"\\COMPUTER\HKLM"), ("COMPUTER", win32con.HKEY_LOCAL_MACHINE, "", None))

  def test_moniker_root_and_body (self):
    self.assertEquals (registry._parse_moniker (r"HKLM\Software\Microsoft"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", None))

  def test_moniker_computer_root_and_body (self):
    self.assertEquals (registry._parse_moniker (r"\\COMPUTER\HKLM\Software\Microsoft"), ("COMPUTER", win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", None))

  def test_moniker_body_only (self):
    with self.assertRaises (registry.x_moniker_no_root):
      registry._parse_moniker (r"Software\Microsoft")

  def test_moniker_default_value (self):
    self.assertEquals (registry._parse_moniker (r"HKLM\Software\Microsoft:"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", ""))

  def test_moniker_value (self):
    self.assertEquals (registry._parse_moniker (r"HKLM\Software\Microsoft:value"), (None, win32con.HKEY_LOCAL_MACHINE, r"Software\Microsoft", "value"))

  def test_moniker_create (self):
    parts = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", "VALUE"
    self.assertEquals (registry._parse_moniker (registry.create_moniker (*parts)), parts)

  def test_moniker_create_named_root (self):
    parts = "COMPUTER", "HKLM", "PATH", "VALUE"
    result = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", "VALUE"
    self.assertEquals (registry._parse_moniker (registry.create_moniker (*parts)), result)

  def test_moniker_create (self):
    parts = "COMPUTER", win32con.HKEY_LOCAL_MACHINE, "PATH", None
    self.assertEquals (registry._parse_moniker (registry.create_moniker (*parts)), parts)

  def test_registry_None (self):
    assert registry.registry (None) is None

  def test_registry_Key (self):
    key = registry.registry ("HKLM")
    assert registry.registry (key) is key

  def test_registry_key_no_value (self):
    assert registry.registry (TEST_KEY + r"\win:sys3", accept_value=False).winsys3 == GUID

  def test_registry_value (self):
    assert registry.registry (TEST_KEY + r":winsys1") == GUID

  def test_registry_string (self):
    assert registry.registry (TEST_KEY).winsys1 == GUID

  def test_registry_other (self):
    with self.assertRaises (registry.x_registry):
      hKey = win32api.RegOpenKey (win32con.HKEY_LOCAL_MACHINE, "Software")
      registry.registry (hKey)

  def test_values (self):
    values = registry.values (TEST_KEY)
    assert next (values) == ('winsys1', GUID)
    assert next (values) == ('winsys2', GUID)

  def test_values_access_denied (self):
    with self.assertRaises (registry.exc.x_access_denied):
      key = registry.registry (TEST_KEY, win32con.KEY_ENUMERATE_SUB_KEYS)
      next (registry.values (key))

  def test_values_ignore_access_denied (self):
    key = registry.registry (TEST_KEY, win32con.KEY_ENUMERATE_SUB_KEYS)
    values = registry.values (key, ignore_access_errors=True)
    assert list (values) == []

  def test_keys (self):
    keys = registry.keys (TEST_KEY)
    assert next (keys) == registry.registry (TEST_KEY) + r"win:sys3"

  def test_keys_access_denied (self):
    with self.assertRaises (registry.exc.x_access_denied):
      key = registry.registry (TEST_KEY, win32con.KEY_NOTIFY)
      keys = registry.keys (key, ignore_access_errors=False)
      next (keys)

  def test_keys_ignore_access_denied (self):
    key = registry.registry (TEST_KEY, win32con.KEY_NOTIFY)
    keys = registry.keys (key, ignore_access_errors=True)
    assert list (keys) == []

  def test_copy_does_not_exist (self):
    key0 = TEST_KEY
    key1 = TEST_KEY1
    registry.copy (key0, key1)
    try:
      assert keys_are_equal (key0, key1)
    finally:
      registry.delete (key1)

  def test_copy_exists_empty (self):
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

  def test_copy_exists_not_empty_keys (self):
    key0 = registry.registry (TEST_KEY)
    key1 = registry.registry (TEST_KEY1)
    assert not bool (key1)
    key1.create ()
    assert bool (key1)
    try:
      key1.create ("winsys4")
      registry.copy (key0, key1)
      assert key0_subset_of_key1 (key0, key1)
    finally:
      key1.delete ()

  def test_copy_exists_not_empty_values (self):
    key0 = registry.registry (TEST_KEY)
    key1 = registry.registry (TEST_KEY1)
    assert not bool (key1)
    key1.create ()
    assert bool (key1)
    try:
      key1.winsys4 = GUID
      registry.copy (key0, key1)
      assert set (set (key1.flat ()) - set (key0.flat ())) == \
        set ([("winsys4", GUID), key1, key1 + "win:sys3", key1 + "winsys2"])
    finally:
      key1.delete ()

  def test_create_does_not_exist (self):
    key1 = registry.registry (TEST_KEY1)
    assert not bool (key1)
    registry.create (key1)
    try:
      assert bool (key1)
    finally:
      key1.delete ()

  def test_create_does_not_exist_deep (self):
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

  def test_create_does_exist (self):
    key = registry.registry (TEST_KEY)
    assert bool (key)
    registry.create (key)
    assert bool (key)

  def test_walk (self):
    walker = registry.walk (TEST_KEY)
    key, subkeys, values = next (walker)
    assert key == registry.registry (TEST_KEY)
    assert list (values) == [("winsys1", GUID), ("winsys2", GUID)]
    key, subkeys, values = next (walker)
    assert key == registry.registry (TEST_KEY) + "win:sys3"
    key, subkeys, values = next (walker)
    assert key == registry.registry (TEST_KEY) + "winsys2"
    assert list (values) == [("winsys2", GUID)]

  def test_walk_access_denied (self):
    with self.assertRaises (registry.exc.x_access_denied):
      key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
      walker = registry.walk (key)
      key, keys, values = next (walker)
      list (keys)

  def test_walk_ignore_access_denied (self):
    key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
    walker = registry.walk (key, ignore_access_errors=True)
    key, keys, values = next (walker)
    list (keys) == [key + "winsys2"]

  def test_flat (self):
    key = registry.registry (TEST_KEY)
    assert list (registry.flat (key)) == [
      key,
      ("winsys1", GUID),
      ("winsys2", GUID),
      key + "win:sys3",
      ("winsys3", GUID),
      key + "winsys2",
      ("winsys2", GUID)
    ]

  def test_flat_access_denied (self):
    with self.assertRaises (registry.exc.x_access_denied):
      key = registry.registry (TEST_KEY, access=registry.REGISTRY_ACCESS.KEY_NOTIFY)
      list (registry.flat (key))

  def test_flat_ignore_access_denied (self):
    remove_access (r"software\winsys\winsys2")
    try:
      key = registry.registry (TEST_KEY)
      assert list (registry.flat (key, ignore_access_errors=True)) == [
        key,
        ("winsys1", GUID),
        ("winsys2", GUID),
        key + "win:sys3",
        ("winsys3", GUID),
      ]
    finally:
      restore_access (r"software\winsys\winsys2")

  def test_parent (self):
    assert registry.parent (TEST_KEY + r"\winsys2") == registry.registry (TEST_KEY)

  def test_identical_functions (self):
    functions = "values keys delete create walk flat copy parent".split ()
    for function in functions:
      assert getattr (registry, function).__code__ is getattr (registry.Registry, function).__code__

  def test_Registry_init (self):
    key = registry.Registry (TEST_KEY, access=win32con.KEY_ALL_ACCESS)
    assert key.moniker == TEST_KEY
    assert key.name == "winsys"
    assert key.access == win32con.KEY_ALL_ACCESS
    assert key.id == registry._parse_moniker (TEST_KEY.lower ())

  def test_Registry_init_access (self):
    for k, v in registry.Registry.ACCESS.items ():
      assert registry.registry (TEST_KEY, k).access == v

  def test_Registry_access (self):
    access = registry.Registry._access
    assert access (None) is None
    assert access (1) == 1
    for k, v in registry.Registry.ACCESS.items ():
      assert registry.registry (TEST_KEY, k).access == v

  def test_Registry_eq (self):
    assert registry.registry (TEST_KEY.upper (), access="R") == registry.registry (TEST_KEY.lower (), access="R")

  def test_Registry_neq (self):
    assert registry.registry (TEST_KEY.upper (), access="R") != registry.registry (TEST_KEY.lower (), access="W")

  def test_Registry_add (self):
    assert registry.registry (TEST_KEY) + "test" == registry.registry (TEST_KEY + registry.sep + "test")

  def test_Registry_pyobject (self):
    assert isinstance (registry.registry (TEST_KEY).pyobject (), pywintypes.HANDLEType)

  def test_Registry_pyobject_not_exists (self):
    with self.assertRaises (registry.exc.x_not_found):
      assert not bool (registry.registry (TEST_KEY + "xxx"))
      registry.registry (TEST_KEY + "xxx").pyobject ()

  def test_Registry_as_string (self):
    key = registry.registry (TEST_KEY)
    assert key.as_string () == key.moniker

  def test_Registry_security (self):
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

  def test_Registry_nonzero_exists (self):
    win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"Software\winsys1")
    try:
      assert bool (registry.registry (TEST_KEY1))
    finally:
      win32api.RegDeleteKey (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"Software"), "winsys1")

  def test_Registry_nonzero_not_exists (self):
    try:
      win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"Software\winsys1")
    except win32api.error as error:
      errno, errctx, errmsg = error.args
      if errno != winerror.ERROR_FILE_NOT_FOUND:
        raise
    else:
      raise RuntimeError ("Key exists but should not")

    assert not bool (registry.registry (TEST_KEY1))

  def test_Registry_dumped (self):
    #
    # Just test it doesn't fall over
    #
    dump = registry.registry ("HKLM").dumped ()

  def test_Registry_get_value (self):
    assert \
      registry.registry (TEST_KEY).get_value ("winsys1") == \
      win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys1")[0]

  def test_Registry_get_key (self):
    assert \
      registry.registry (TEST_KEY).get_key ("winsys1") == \
      registry.registry (TEST_KEY + r"\winsys1")

  def test_Registry_getattr_value (self):
    value, type = win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys1")
    assert registry.registry (TEST_KEY).winsys1 == value

  def test_Registry_getattr_value_shadows_key (self):
    value, type = win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys2")
    assert registry.registry (TEST_KEY).winsys2 == value

  def test_Registry_getattr_key (self):
    win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"software\winsys\winsys3")
    try:
      assert registry.registry (TEST_KEY).winsys3 == registry.registry (TEST_KEY).get_key ("winsys3")
    finally:
      win32api.RegDeleteKey (win32con.HKEY_CURRENT_USER, r"Software\winsys\winsys3")

  def setup_set_value (self):
    try:
      win32api.RegDeleteValue (
        win32api.RegOpenKeyEx (
          win32con.HKEY_CURRENT_USER,
          r"Software\winsys",
          0,
          win32con.KEY_ALL_ACCESS
        ),
        "winsys4"
      )
    except win32api.error as error:
      errno, errctx, errmsg = error.args
      if errno == 2:
        pass
      else:
        raise

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_type (self):
    registry.registry (TEST_KEY).set_value ("winsys4", b"abc", win32con.REG_BINARY)
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == (b"abc", win32con.REG_BINARY)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_int (self):
    registry.registry (TEST_KEY).set_value ("winsys4", 1)
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == (1, win32con.REG_DWORD)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_multi (self):
    registry.registry (TEST_KEY).set_value ("winsys4", ['a', 'b', 'c'])
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == (['a', 'b', 'c'], win32con.REG_MULTI_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_expand_even_percent (self):
    registry.registry (TEST_KEY).set_value ("winsys4", "%TEMP%")
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == ("%TEMP%", win32con.REG_EXPAND_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_expand_odd_percent (self):
    registry.registry (TEST_KEY).set_value ("winsys4", "50%")
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == ("50%", win32con.REG_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_empty_string (self):
    registry.registry (TEST_KEY).set_value ("winsys4", "")
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == ("", win32con.REG_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_non_empty_string (self):
    registry.registry (TEST_KEY).set_value ("winsys4", "winsys")
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == ("winsys", win32con.REG_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_none (self):
    registry.registry (TEST_KEY).set_value ("winsys4", None)
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), "winsys4") == ("", win32con.REG_SZ)

  #~ @with_setup (setup_set_value)
  def test_Registry_set_value_default (self):
    registry.registry (TEST_KEY).set_value ("", "test")
    assert win32api.RegQueryValueEx (win32api.RegOpenKey (win32con.HKEY_CURRENT_USER, r"software\winsys"), None) == ("test", win32con.REG_SZ)

  def test_Registry_add (self):
    key0 = registry.registry (TEST_KEY)
    new_key = key0.create ("winsys1")
    assert new_key == key0 + "winsys1"

  def test_Registry_from_string (self):
    key = registry.Registry.from_string (TEST_KEY)
    assert key.moniker == TEST_KEY
    assert key.access == registry.Registry._access (registry.Registry.DEFAULT_ACCESS)
    assert key.id == registry._parse_moniker (TEST_KEY.lower ())

  def test_Registry_from_string_value (self):
    assert registry.Registry.from_string (TEST_KEY + ":winsys1") == registry.Registry.from_string (TEST_KEY).get_value ("winsys1")

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
