import win32net
import win32netcon

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
