import os, sys
import utils

import win32api
import win32security
import ntsecuritycon

from winsys import _tokens

token0 = None
def setup ():
  utils.create_user ("alice", "password")
  utils.create_group ("winsys")
  utils.add_user_to_group ("alice", "winsys")
  global token0
  token0 = win32security.OpenProcessToken (win32api.GetCurrentProcess (), ntsecuritycon.MAXIMUM_ALLOWED)
  session_id = win32security.GetTokenInformation (token0, win32security.Token

def teardown ():
  utils.delete_user ("alice")
  utils.delete_group ("winsys")

def test_token_None ():
  assert _tokens.token (None) is None

def test_token_default ():
  #
  # For now, make sure this doesn't fail
  #
  token = _tokens.token ()
  print token.Statistics['AuthenticationId']
  
  assert False