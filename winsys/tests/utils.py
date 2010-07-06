import os, sys
import contextlib
import io

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
  except win32net.error as error:
    number, context, message = error.args
    if number != 2221:
      raise
  win32net.NetUserAdd (None, 1, user_info)

def create_group (group):
  group_info = dict (
    name = group
  )
  try:
    win32net.NetLocalGroupDel (None, group)
  except win32net.error as error:
    number, context, message = error.args
    if number != 2220:
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
  except win32net.error as error:
    errno, errctx, errmsg = error.args
    if errno != 2221: raise

def delete_group (group):
  try:
    win32net.NetLocalGroupDel (None, group)
  except win32net.error as error:
    errno, errctx, errmsg = error.args
    if errno != 2220: raise

def change_priv (priv_name, enable=True):
  hToken = win32security.OpenProcessToken (
    win32api.GetCurrentProcess (),
    ntsecuritycon.MAXIMUM_ALLOWED
  )
  win32security.AdjustTokenPrivileges (
    hToken,
    False,
    [(
      win32security.LookupPrivilegeValue (None, priv_name),
      win32security.SE_PRIVILEGE_ENABLED if enable else 0
    )]
  )

@contextlib.contextmanager
def fake_stdout ():
  _stdout, sys.stdout = sys.stdout, io.StringIO ()
  yield sys.stdout
  sys.stdout = _stdout

