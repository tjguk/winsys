import os, sys
import utils

import win32api
import win32security
import ntsecuritycon

from winsys import _tokens

token0 = None
alice = None
def setup ():
  utils.create_user ("alice", "Passw0rd")
  utils.create_group ("winsys")
  utils.add_user_to_group ("alice", "winsys")
  global token0
  token0 = win32security.OpenProcessToken (win32api.GetCurrentProcess (), ntsecuritycon.MAXIMUM_ALLOWED)
  global alice
  alice, _, _ = win32security.LookupAccountName (None, "alice")

me, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())

def teardown ():
  utils.delete_user ("alice")
  utils.delete_group ("winsys")

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

def test_Token_unnimpersonate ():
  hToken = win32security.LogonUser (
    "alice",
    "",
    "Passw0rd",
    win32security.LOGON32_LOGON_NETWORK,
    win32security.LOGON32_PROVIDER_DEFAULT
  )
  token = _tokens.Token (hToken)
  win32security.ImpersonateLoggedOnUser (token.pyobject ())
  assert token.Owner.pyobject () == alice
  win32security.RevertToSelf () ##token.unimpersonate ()
  print token.Owner.pyobject ()
  print me
  print alice
  assert token.Owner.pyobject () == me