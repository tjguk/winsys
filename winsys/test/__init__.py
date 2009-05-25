import os, sys
import nose
import utils

def setup ():
  utils.create_user ("alice", "Passw0rd")
  utils.create_group ("winsys")
  utils.add_user_to_group ("alice", "winsys")

def teardown ():
  utils.delete_user ("alice")
  utils.delete_group ("winsys")

def run ():
  here = os.path.dirname (__file__)
  sys.exit (nose.main (argv=["--where", here]))

if __name__ == '__main__':
  run ()
