# -*- coding: iso-8859-1 -*-
u"""Provide unified access to the different sets of constants used by
the winsys module. Some of them are provided by modules within the
pywin32 package. Others belong to those sets but are not present in
the modules. Still others are not present at all within pywin32 and
are added here manually.

The constants are grouped together into named Constants classes
which combine the effect of being a namespace and also providing
functions to list the constant name or names given a value, which
is useful when displaying Win32 structures.
"""
import re

from win32com.taskscheduler import taskscheduler
from win32com.shell import shellcon
import win32con
import win32event
import win32evtlog
import win32file
import winioctlcon
import win32security
import ntsecuritycon
import fnmatch

def from_pattern (pattern, name):
  u"""Helper function to find the common pattern among a group
  of like-named constants. eg if the pattern is FILE_ACCESS_*
  then the part of the name after FILE_ACCESS_ will be returned.
  """
  if pattern is None:
    return name
  else:
    return re.search (pattern.replace ("*", r"(\w+)"), name).group (1)

class Constants (object):
  u"""Provide a dict-like interface for a group of related
  constants. These can come from a module or other namespace according
  to a wildcard name, or can be added as a list of (unrelated) names from 
  a namespace or can simply be a raw dictionary of name-value pairs.
  """
  
  def __init__ (self, dict_initialiser):
    u"""Build an internal structure from a dictionary-like
    set of initial values.
    """
    self._dict = dict (dict_initialiser)

  def __getitem__ (self, attribute):
    u"""Act as a dictionary and as a namespace so that calls like 
    FILE_ACCESS["READ"] and FILE_ACCESS.READ will both succeed.
    """
    return self._dict[attribute]
  __getattr__ = __getitem__
  
  def __repr__ (self):
    return "<Constants: %r>" % self._dict
    
  def __str__ (self):
    return "<Constants: %s>" % ", ".join (self._dict.keys ())
    
  def __contains__ (self, attribute):
    return attribute in self.keys ()
  
  def update (self, other):
    u"""Act as a dict for updates so that several constant sets may
    be merged into one.
    """
    self._dict.update (dict (other.items ()))
    
  def items (self):
    return self._dict.items ()
    
  def keys (self):
    return self._dict.keys ()
    
  def values (self):
    return self._dict.values ()
  
  @classmethod
  def from_dict (cls, d, pattern=None):
    u"""Factory method to return a class instance from a dictionary-like set of values.
    If a pattern is passed in, use the distinguished part of the name (the part
    which matches the wildcard) as the key name.
    """
    return cls ((from_pattern (pattern, key), value) for (key, value) in d.items ())
  
  @classmethod
  def from_list (cls, keys, namespace=win32security, pattern=None):
    u"""Factory method to return a class instance from a list-like set of values
    within a namespace. Hands off to the from_dict factory.
    """
    return cls ((from_pattern (pattern, key), getattr (namespace, key, None)) for key in keys)

  @classmethod
  def from_pattern (cls, pattern=u"*", excluded=[], namespace=win32security):
    u"""Factory method to return a class instance from a wildcard name pattern. This is
    the most common method of constructing a list of constants by passing in, eg,
    FILE_ATTRIBUTE_* and the win32file module as the namespace.
    """
    return cls (
      (from_pattern (pattern, key), getattr (namespace, key)) for \
        key in dir (namespace) if \
        fnmatch.fnmatch (key, pattern) and \
        key not in excluded
    )
    
  def names (self, patterns=[u"*"]):    
    u"""From a list of patterns, return the matching names from the
    list of constants. A single string is considered as though a
    list of one.
    """
    if isinstance (patterns, basestring):
      patterns = [patterns]
    for name in self._dict.keys ():
      for pattern in patterns:
        if fnmatch.fnmatch (name, pattern):
          yield name
  
  def names_from_value (self, value, patterns=[u"*"]):
    u"""From a number representing the or-ing of several integer values,
    work out which of the constants make up the number using the pattern
    to filter the "classes" or constants present in the dataset.
    """
    return [name for name in self.names (patterns) if value & self[name]]
    
  def name_from_value (self, value, patterns=[u"*"]):
    u"""Find the one name in the set of constants (optionally qualified by pattern)
    which matches value.
    """
    for name in self.names (patterns):
      if self[name] == value:
        return name
    else:
      raise KeyError, u"No constant matching name %s and value %d" % (patterns, value)
      
  def values_from_value (self, value, patterns=["*"]):
    """Return the list of values which make up the combined value
    """
    return [self._dict[name] for name in names_from_value (value, patterns)]

ACE_FLAG = Constants.from_list ([u"CONTAINER_INHERIT_ACE", u"INHERIT_ONLY_ACE", u"INHERITED_ACE", u"NO_PROPAGATE_INHERIT_ACE", u"OBJECT_INHERIT_ACE"], pattern=u"*_ACE")
ACE_TYPE = Constants.from_pattern (u"*_ACE_TYPE")
DACE_TYPE = Constants.from_pattern (u"ACCESS_*_ACE_TYPE")
SACE_TYPE = Constants.from_pattern (u"SYSTEM_*_ACE_TYPE")
PRIVILEGE_ATTRIBUTE = Constants.from_pattern (u"SE_PRIVILEGE_*")
PRIVILEGE = Constants.from_pattern (u"SE_*_NAME")
WELL_KNOWN_SID = Constants.from_pattern (u"Win*Sid")
SE_OBJECT_TYPE = Constants.from_list ([
  u"SE_UNKNOWN_OBJECT_TYPE",
  u"SE_FILE_OBJECT",
  u"SE_SERVICE",
  u"SE_PRINTER",
  u"SE_REGISTRY_KEY",
  u"SE_LMSHARE",
  u"SE_KERNEL_OBJECT",
  u"SE_WINDOW_OBJECT",
  u"SE_DS_OBJECT",
  u"SE_DS_OBJECT_ALL",
  u"SE_PROVIDER_DEFINED_OBJECT",
  u"SE_WMIGUID_OBJECT",
  u"SE_REGISTRY_WOW64_32KEY"
], pattern=u"SE_*")
SECURITY_INFORMATION = Constants.from_pattern (u"*_SECURITY_INFORMATION")
LOGON = Constants.from_pattern (u"LOGON32_*")
GENERAL = Constants.from_dict (dict (
  MAXIMUM_ALLOWED=ntsecuritycon.MAXIMUM_ALLOWED,
  INFINITE=win32event.INFINITE
))
REVISION = Constants.from_list ([u"ACL_REVISION", u"ACL_REVISION_DS", u"SDDL_REVISION_1"])
TOKEN_FLAG = Constants.from_pattern (u"TOKEN_*")
SID_TYPE = Constants.from_pattern (u"SidType*")

ACCESS = Constants.from_list ([
  u"DELETE",
  u"READ_CONTROL",
  u"WRITE_DAC",
  u"WRITE_OWNER",
  u"SYNCHRONIZE"
], namespace=ntsecuritycon)
GENERIC_ACCESS = Constants.from_pattern (u"GENERIC_*", namespace=ntsecuritycon)
STANDARD_ACCESS = Constants.from_list ([u"STANDARD_RIGHTS_READ", u"STANDARD_RIGHTS_WRITE", u"SYNCHRONIZE"], namespace=ntsecuritycon)
FILE_ACCESS = Constants.from_pattern ("FILE_*", namespace=ntsecuritycon)
FILE_ACCESS.update (STANDARD_ACCESS)
FILE_ACCESS.update (GENERIC_ACCESS)
FILE_ACCESS.update (ACCESS)
FILE_SHARE = Constants.from_pattern (u"FILE_SHARE_*", namespace=win32file)

SCHEDULED_TASK_ERROR = Constants.from_pattern (u"SCHED_E_*", namespace=taskscheduler)
TASKPAGE = Constants.from_pattern (u"TASKPAGE_*", namespace=taskscheduler)
TASK = Constants.from_pattern (u"TASK_*", namespace=taskscheduler)
TASK_PRIORITY = Constants.from_pattern (u"*_PRIORITY_CLASS", namespace=taskscheduler)

FILE_NOTIFY_CHANGE = Constants.from_pattern (u"FILE_NOTIFY_CHANGE_*", namespace=win32con)
FILE_ACTION = Constants.from_dict (dict (
  ADDED = 1,
  REMOVED = 2,
  MODIFIED = 3,
  RENAMED_OLD_NAME = 4,
  RENAMED_NEW_NAME = 5
))
FILE_ATTRIBUTE = Constants.from_pattern (u"FILE_ATTRIBUTE_*", namespace=win32file)
FILE_ATTRIBUTE.update (dict (
  ENCRYPTED=0x00004000, 
  REPARSE_POINT=0x00000400,
  SPARSE_FILE=0x00000200,
  VIRTUAL=0x00010000,
  NOT_CONTENT_INDEXES=0x00002000,
))
PROGRESS = Constants.from_pattern (u"PROGRESS_*", namespace=win32file)
MOVEFILE = Constants.from_pattern (u"MOVEFILE_*", namespace=win32file)
FILE_FLAG = Constants.from_pattern (u"FILE_FLAG_*", namespace=win32con)
FILE_CREATION = Constants.from_list ([u"CREATE_ALWAYS", u"CREATE_NEW", u"OPEN_ALWAYS", u"OPEN_EXISTING", u"TRUNCATE_EXISTING"], namespace=win32con)

COMPRESSION_FORMAT = Constants.from_dict (dict (
  NONE = (0x0000),   
  DEFAULT = (0x0001),   
  LZNT1 = (0x0002)
))
FSCTL = Constants.from_pattern (u"FSCTL_*", namespace=winioctlcon)

SD_CONTROL = Constants.from_list ([
  #~ "SE_DACL_AUTO_INHERIT_REQ", 
  u"SE_DACL_AUTO_INHERITED", 
  u"SE_DACL_DEFAULTED", 
  u"SE_DACL_PRESENT", 
  u"SE_DACL_PROTECTED", 
  u"SE_GROUP_DEFAULTED",
  u"SE_OWNER_DEFAULTED",
  #~ "SE_RM_CONTROL_VALID",
  #~ "SE_SACL_AUTO_INHERIT_REQ",
  u"SE_SACL_AUTO_INHERITED",
  u"SE_SACL_DEFAULTED",
  u"SE_SACL_PRESENT",
  u"SE_SACL_PROTECTED",
  u"SE_SELF_RELATIVE"
], pattern=u"SE_*")

EXTENDED_NAME = Constants.from_pattern (u"Name*", namespace=win32con)

VOLUME_FLAG = Constants.from_dict (dict (
  FILE_CASE_SENSITIVE_SEARCH      = 0x00000001,
  FILE_CASE_PRESERVED_NAMES       = 0x00000002,
  FILE_UNICODE_ON_DISK            = 0x00000004,
  FILE_PERSISTENT_ACLS            = 0x00000008,
  FILE_FILE_COMPRESSION           = 0x00000010,
  FILE_VOLUME_QUOTAS              = 0x00000020,
  FILE_SUPPORTS_SPARSE_FILES      = 0x00000040,
  FILE_SUPPORTS_REPARSE_POINTS    = 0x00000080,
  FILE_SUPPORTS_REMOTE_STORAGE    = 0x00000100,
  FILE_VOLUME_IS_COMPRESSED       = 0x00008000,
  FILE_SUPPORTS_OBJECT_IDS        = 0x00010000,
  FILE_SUPPORTS_ENCRYPTION        = 0x00020000,
  FILE_NAMED_STREAMS              = 0x00040000,
  FILE_READ_ONLY_VOLUME           = 0x00080000,
  FILE_SEQUENTIAL_WRITE_ONCE      = 0x00100000,
  FILE_SUPPORTS_TRANSACTIONS      = 0x00200000  
), pattern=u"FILE_*")
DRIVE_TYPE = Constants.from_pattern (u"DRIVE_*", namespace=win32file)

REGISTRY_HIVE = Constants.from_list ([
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
REGISTRY_ACCESS = Constants.from_list ([
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
REGISTRY_VALUE_TYPE = Constants.from_list ([
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

EVENTLOG_READ = Constants.from_pattern (u"EVENTLOG_*_READ", namespace=win32evtlog)
EVENTLOG_TYPE = Constants.from_pattern (u"EVENTLOG_*_TYPE", namespace=win32evtlog)
EVENTLOG_TYPE.update (dict (
  AUDIT_FAILURE = win32evtlog.EVENTLOG_AUDIT_FAILURE,
  AUDIT_SUCCESS = win32evtlog.EVENTLOG_AUDIT_SUCCESS
))


#
# Constants used by SHBrowseForFolder
#
BIF = Constants.from_dict (dict (
  BIF_RETURNONLYFSDIRS   = 0x0001,
  BIF_DONTGOBELOWDOMAIN  = 0x0002,
  BIF_STATUSTEXT         = 0x0004,
  BIF_RETURNFSANCESTORS  = 0x0008,
  BIF_EDITBOX            = 0x0010,
  BIF_VALIDATE           = 0x0020,
  BIF_NEWDIALOGSTYLE     = 0x0040,
  BIF_BROWSEINCLUDEURLS  = 0x0080,
  BIF_UAHINT             = 0x0100,
  BIF_NONEWFOLDERBUTTON  = 0x0200,
  BIF_NOTRANSLATETARGETS = 0x0400,
  BIF_BROWSEFORCOMPUTER  = 0x1000,
  BIF_BROWSEFORPRINTER   = 0x2000,
  BIF_BROWSEINCLUDEFILES = 0x4000,
  BIF_SHAREABLE          = 0x8000
), pattern=u"BIF_*")
BIF.update (dict (USENEWUI = BIF.NEWDIALOGSTYLE | BIF.EDITBOX))
BFFM = Constants.from_pattern (u"BFFM_*", namespace=shellcon)

#
# Constants used by WaitFor*Objects
#
WAIT = Constants.from_pattern (u"WAIT_*", namespace=win32event)
WAIT.update (dict (INFINITE=win32event.INFINITE))