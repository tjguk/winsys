import os, sys
import unittest2 as unittest

import win32api
import win32security

from winsys import accounts
from winsys.tests import utils

class TestAccounts (unittest.TestCase):

  def setUp (self):
    utils.create_user ("alice", "Passw0rd")
    utils.create_group ("winsys")
    utils.add_user_to_group ("alice", "winsys")

  def tearDown (self):
    utils.delete_user ("alice")
    utils.delete_group ("winsys")

  def test_principal_None (self):
    assert accounts.principal (None) is None

  def test_principal_sid (self):
    everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
    assert accounts.principal (everyone).pyobject () == everyone

  def test_principal_Principal (self):
    everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
    principal = accounts.Principal (everyone)
    assert accounts.principal (principal) is principal

  def test_principal_string (self):
    everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
    assert accounts.principal ("Everyone") == everyone

  def test_principal_invalid (self):
    with self.assertRaises (accounts.exc.x_not_found):
      accounts.principal (object)

  def text_context (self):
    assert win32api.GetUserName () != "alice"
    with accounts.principal ("alice").impersonate ("Passw0rd"):
      assert win32api.GetUserName () == "alice"
    assert win32api.GetUserName () != "alice"

if __name__ == "__main__":
  unittest.main ()
  if sys.stdout.isatty (): raw_input ("Press enter...")
