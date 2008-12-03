import os, sys

import win32api
import win32security
import ntsecuritycon

from winsys import _tokens

token0 = None
alice = None
def setup ():
  global token0
  token0 = win32security.OpenProcessToken (win32api.GetCurrentProcess (), ntsecuritycon.MAXIMUM_ALLOWED)
  global alice
  alice, _, _ = win32security.LookupAccountName (None, "alice")

me, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())

def test_token_None ():
  assert _tokens.token (None) is None

def test_token_default ():
  assert _tokens.token ().Statistics['AuthenticationId'] == win32security.GetTokenInformation (token0, win32security.TokenStatistics)['AuthenticationId']
  assert _tokens.token ().Origin == win32security.GetTokenInformation (token0, win32security.TokenOrigin)

def test_Token_dump ():
  #
  # This is a bit crude, but we're hoping to exercise all of the
  # token attributes this way.
  #
  _tokens.token ().dump ()

def test_Token_impersonate ():
  alice, system, type = win32security.LookupAccountName (None, "alice")
  hToken = win32security.LogonUser (
    "alice",
    "",
    "Passw0rd",
    win32security.LOGON32_LOGON_NETWORK,
    win32security.LOGON32_PROVIDER_DEFAULT
  )
  token = _tokens.Token (hToken)
  try:
    token.impersonate ()
    assert token.Owner.pyobject () == alice
  finally:
    win32security.RevertToSelf ()

def test_Token_unimpersonate ():
  hToken = win32security.LogonUser (
    "alice",
    "",
    "Passw0rd",
    win32security.LOGON32_LOGON_NETWORK,
    win32security.LOGON32_PROVIDER_DEFAULT
  )
  win32security.ImpersonateLoggedOnUser (_tokens.Token (hToken).pyobject ())
  assert _tokens.token ().Owner.pyobject () == alice
  win32security.RevertToSelf ()
  assert _tokens.token ().Owner.pyobject () == me

def test_Token_change_privileges_enable ():
  for disabled_priv, status in win32security.GetTokenInformation (token0, win32security.TokenPrivileges):
    if not status & win32security.SE_PRIVILEGE_ENABLED: break
  
  was_enabled, was_disabled = _tokens.Token (token0).change_privileges (enable_privs=[disabled_priv])
  
  for priv, status in win32security.GetTokenInformation (token0, win32security.TokenPrivileges):
    if priv == disabled_priv:
      assert status & win32security.SE_PRIVILEGE_ENABLED
  
  _tokens.Token (token0).change_privileges (was_enabled, was_disabled)

def test_Token_change_privileges_disable ():
  for enabled_priv , status in win32security.GetTokenInformation (token0, win32security.TokenPrivileges):
    if status & win32security.SE_PRIVILEGE_ENABLED: break
  
  was_enabled, was_disabled = _tokens.Token (token0).change_privileges (disable_privs=[enabled_priv])
  
  for priv, status in win32security.GetTokenInformation (token0, win32security.TokenPrivileges):
    if priv == enabled_priv:
      assert not status & win32security.SE_PRIVILEGE_ENABLED
  
  _tokens.Token (token0).change_privileges (was_enabled, was_disabled)
