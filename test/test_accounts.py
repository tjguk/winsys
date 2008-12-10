import os, sys

import win32security
from nose.tools import *

from winsys import accounts

def setup ():
  pass

def teardown ():
  pass

def test_principal_None ():
  assert accounts.principal (None) is None

def test_principal_sid ():
  everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
  assert accounts.principal (everyone).pyobject () == everyone

def test_principal_Principal ():
  everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
  principal = accounts.Principal (everyone)
  assert accounts.principal (principal) is principal

def test_principal_string ():
  everyone, domain, type = win32security.LookupAccountName (None, "Everyone")
  assert accounts.principal ("Everyone") == everyone
  
@raises (accounts.x_not_found)
def test_principal_invalid ():
  accounts.principal (object)

if __name__ == '__main__':
  import nose
  nose.runmodule () 
  raw_input ("Press enter...")
