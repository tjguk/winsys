import os, sys

from nose.tools import *

from winsys import _lsa

def setup ():
  pass

def teardown ():
  pass

def test_LSA_logon_sessions ():
  for logon_session in _lsa.LSA.logon_sessions ():
    logon_session.dump ()
