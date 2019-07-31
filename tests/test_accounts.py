# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys
from winsys._compat import unittest

import win32api
import win32security

from winsys.tests import utils as testutils
from winsys import accounts

@unittest.skipUnless(testutils.i_am_admin(), "These tests must be run as Administrator")
class TestAccounts(unittest.TestCase):

    def setUp(self):
        testutils.create_user("alice", "Passw0rd")
        testutils.create_group("winsys")
        testutils.add_user_to_group("alice", "winsys")

    def tearDown(self):
        testutils.delete_user("alice")
        testutils.delete_group("winsys")

    def test_principal_None(self):
        assert accounts.principal(None) is None

    def test_principal_sid(self):
        everyone, domain, type = win32security.LookupAccountName(None, "Everyone")
        assert accounts.principal(everyone).pyobject() == everyone

    def test_principal_Principal(self):
        everyone, domain, type = win32security.LookupAccountName(None, "Everyone")
        principal = accounts.Principal(everyone)
        assert accounts.principal(principal) is principal

    def test_principal_string(self):
        everyone, domain, type = win32security.LookupAccountName(None, "Everyone")
        assert accounts.principal("Everyone") == everyone

    def test_principal_invalid(self):
        with self.assertRaises(accounts.exc.x_not_found):
            accounts.principal(object)

    def text_context(self):
        assert win32api.GetUserName() != "alice"
        with accounts.principal("alice").impersonate("Passw0rd"):
            assert win32api.GetUserName() == "alice"
        assert win32api.GetUserName() != "alice"

if __name__ == "__main__":
    unittest.main()
    if sys.stdout.isatty(): raw_input("Press enter...")
