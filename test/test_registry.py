from nose.tools import *
import winerror
import win32api
import win32con
import win32security
import uuid

from winsys import registry

GUID = str (uuid.uuid1 ())
def setup ():
  win32api.RegCreateKey (win32con.HKEY_CURRENT_USER, r"Software\winsys")
  hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.KEY_WRITE)
  win32api.RegSetValueEx (hKey, "winsys", None, win32con.REG_SZ, GUID)
  hSubkey = win32api.RegCreateKey (hKey, "winsys2")
  win32api.RegSetValueEx (hSubkey, "winsys2", None, win32con.REG_SZ, GUID)
  
def teardown ():
  print "*** tearing down..."
  try:
    hKey = win32api.RegOpenKeyEx (win32con.HKEY_CURRENT_USER, r"Software\winsys", 0, win32con.READ_CONTROL|win32con.WRITE_DAC|win32con.DELETE)
    win32security.SetSecurityInfo (hKey, win32security.SE_REGISTRY_KEY, win32security.DACL_SECURITY_INFORMATION, None, None, None, None)
    win32api.RegDeleteKey (win32con.HKEY_CURRENT_USER, r"Software\winsys")
  except win32api.error, (errno, errctx, errmsg):
    if errno == winerror.ERROR_FILE_NOT_FOUND:
      pass
    else:
      raise
  
#
# test disabled until I can figure out a way to make it fail!
#
#~ def test_moniker_ill_formed ():
  #~ assert_raises (registry.x_moniker_ill_formed, registry.parse_moniker, r"IN\VA:LID\MONI\KER")
  
def test_moniker_computer_only ():
  assert_raises (registry.x_moniker_no_root, registry.parse_moniker, r"\\computer")
    
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

def test_moniker_body_only ():
  assert_raises (registry.x_moniker_no_root, registry.parse_moniker, r"Software\Microsoft")

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

def test_key_None ():
  assert (registry.key (None) is None)
  
def test_key_Key ():
  key = registry.key ("HKLM")
  assert (registry.key (key) is key)

def test_key_HKey ():
  hKey = win32api.RegOpenKey (win32con.HKEY_LOCAL_MACHINE, "Software")
  assert (registry.key (hKey).hKey == hKey)
  
def test_key_string ():
  assert (registry.key (r"HKCU\Software\winsys").winsys == GUID)

def remove_access ():
  s = registry.key (r"HKCU\Software\winsys").security ("D")
  s.break_inheritance (False)
  s.to_object ()
  
def restore_access ():
  root = registry.key (r"HKCU\Software\winsys")
  for k, _, _ in root.walk (access=win32con.READ_CONTROL|win32con.WRITE_DAC):
    print "Restore access to", k
    s = k.security ("D")
    s.dacl = None
    s.to_object ()

def test_values_access_denied ():
  remove_access ()
  try:
    registry.values (registry.key (r"HKCU\Software\winsys"))
  except registry.x_access_denied:
    result = True
  else:
    result = False
  restore_access ()
  
  if not result:
    raise RuntimeError

if __name__ == '__main__':
  import nose
  nose.main ()
