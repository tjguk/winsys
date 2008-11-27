import utils

def setup ():
  utils.create_user ("alice", "Passw0rd")
  utils.create_group ("winsys")
  utils.add_user_to_group ("alice", "winsys")

def teardown ():
  utils.delete_user ("alice")
  utils.delete_group ("winsys")
