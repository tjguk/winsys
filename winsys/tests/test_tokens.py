# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys
from winsys._compat import unittest

import win32api
import win32security
import ntsecuritycon

from winsys.tests import utils as testutils
from winsys._security import _tokens

@unittest.skipUnless(testutils.i_am_admin(), "These tests must be run as Administrator")
class TestTokens (unittest.TestCase):

  me, _, _ = win32security.LookupAccountName (None, win32api.GetUserName ())

  def setUp (self):
    testutils.create_user ("alice", "Passw0rd")
    testutils.create_group ("winsys")
    testutils.add_user_to_group ("alice", "winsys")
    self.token0 = win32security.OpenProcessToken (win32api.GetCurrentProcess (), ntsecuritycon.MAXIMUM_ALLOWED)
    self.alice, _, _ = win32security.LookupAccountName (None, "alice")

  def tearDown (self):
    testutils.delete_user ("alice")
    testutils.delete_group ("winsys")

  def test_token_None (self):
    assert _tokens.token (None) is None

  def test_token_default (self):
    assert _tokens.token ().Statistics['AuthenticationId'] == win32security.GetTokenInformation (self.token0, win32security.TokenStatistics)['AuthenticationId']
    assert _tokens.token ().Origin == win32security.GetTokenInformation (self.token0, win32security.TokenOrigin)

  def test_Token_dump (self):
    #
    # This is a bit crude, but we're hoping to exercise all of the
    # token attributes this way.
    #
    dumped = _tokens.token ().dumped (0)

  def test_Token_impersonate (self):
    self.alice, system, type = win32security.LookupAccountName (None, "alice")
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
      assert token.Owner.pyobject () == self.alice
    finally:
      win32security.RevertToSelf ()

  def test_Token_unimpersonate (self):
    hToken = win32security.LogonUser (
      "alice",
      "",
      "Passw0rd",
      win32security.LOGON32_LOGON_NETWORK,
      win32security.LOGON32_PROVIDER_DEFAULT
    )
    me = _tokens.token ().Owner.pyobject ()
    win32security.ImpersonateLoggedOnUser (_tokens.Token (hToken).pyobject ())
    self.assertEquals (_tokens.token ().Owner.pyobject (), self.alice)
    win32security.RevertToSelf ()
    self.assertEquals (_tokens.token ().Owner.pyobject (), me)

  def test_Token_change_privileges_enable (self):
    for disabled_priv, status in win32security.GetTokenInformation (self.token0, win32security.TokenPrivileges):
      if not status & win32security.SE_PRIVILEGE_ENABLED: break

    was_enabled, was_disabled = _tokens.Token (self.token0).change_privileges (enable_privs=[disabled_priv])

    for priv, status in win32security.GetTokenInformation (self.token0, win32security.TokenPrivileges):
      if priv == disabled_priv:
        assert status & win32security.SE_PRIVILEGE_ENABLED

    _tokens.Token (self.token0).change_privileges (was_enabled, was_disabled)

  def test_Token_change_privileges_disable (self):
    for enabled_priv , status in win32security.GetTokenInformation (self.token0, win32security.TokenPrivileges):
      if status & win32security.SE_PRIVILEGE_ENABLED: break

    was_enabled, was_disabled = _tokens.Token (self.token0).change_privileges (disable_privs=[enabled_priv])

    for priv, status in win32security.GetTokenInformation (self.token0, win32security.TokenPrivileges):
      if priv == enabled_priv:
        assert not status & win32security.SE_PRIVILEGE_ENABLED

    _tokens.Token (self.token0).change_privileges (was_enabled, was_disabled)

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
