import win32security
import ntsecuritycon
import win32con
import win32api

def wrapped (fn, *args):
  return fn (*args)

owner, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())

sa = wrapped (win32security.SECURITY_ATTRIBUTES)
sa.bInheritHandle = True
owner = me
group = None
dacl = win32security.ACL ()

dacl = None if self._dacl is core.UNSET else self._dacl.pyobject (include_inherited=include_inherited)
#~ sacl = None if self._sacl is core.UNSET else self._sacl.pyobject (include_inherited=include_inherited)
if owner:
  sa.SetSecurityDescriptorOwner (owner, False)

#
# The first & last flags on the Set...acl methods represent,
# respectively, whether the ACL is present (!) and whether
# it's the result of inheritance.
#
sa.SetSecurityDescriptorDacl (True, dacl, False)
#~ sa.SetSecurityDescriptorSacl (True, sacl, False)
#~ if self.inherits:
  #~ sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, 0)
#~ else:
  #~ sa.SetSecurityDescriptorControl (SD_CONTROL.DACL_PROTECTED, SD_CONTROL.DACL_PROTECTED)
