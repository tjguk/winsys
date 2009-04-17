import win32security

from winsys import constants

REVISION = constants.Constants.from_list ([
  u"ACL_REVISION", 
  u"ACL_REVISION_DS", 
  u"SDDL_REVISION_1"
], namespace=win32security)
