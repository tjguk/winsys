import win32api
import win32net
import win32netcon
import win32security
import ntsecuritycon

def create_user (user, password):
  user_info = dict (
    name = user,
    password = password,
    priv = win32netcon.USER_PRIV_USER,
    home_dir = None,
    comment = None,
    flags = win32netcon.UF_SCRIPT,
    script_path = None
  )
  try:
    win32net.NetUserDel (None, user)
  except win32net.error, (number, context, message):
    if number <> 2221:
      raise
  win32net.NetUserAdd (None, 1, user_info)

def create_group (group):
  group_info = dict (
    name = group
  )
  try:
    win32net.NetLocalGroupDel (None, group)
  except win32net.error, (number, context, message):
    if number <> 2220:
      raise
  win32net.NetLocalGroupAdd (None, 0, group_info)

def add_user_to_group (user, group):
  user_group_info = dict (
    domainandname = user
  )
  win32net.NetLocalGroupAddMembers (None, group, 3, [user_group_info])

def delete_user (user):
  try:
    win32net.NetUserDel (None, user)
  except win32net.error, (errno, errctx, errmsg):
    if errno != 2221: raise

def delete_group (group):
  try:
    win32net.NetLocalGroupDel (None, group)
  except win32net.error, (errno, errctx, errmsg):
    if errno != 2220: raise

def change_priv (priv_name, enable=True):
  hToken = win32security.OpenProcessToken (
    win32api.GetCurrentProcess (), 
    ntsecuritycon.MAXIMUM_ALLOWED
  )
  #
  # If you don't enable SeSecurity, you won't be able to
  # read SACL in this process.
  #
  win32security.AdjustTokenPrivileges ( 
    hToken,
    False, 
    [(
      win32security.LookupPrivilegeValue (None, win32security.SE_SECURITY_NAME), 
      win32security.SE_PRIVILEGE_ENABLED if enable else 0
    )]
  )
