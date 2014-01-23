# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import win32security

from winsys import constants

REVISION = constants.Constants.from_list([
    "ACL_REVISION",
    "ACL_REVISION_DS",
    "SDDL_REVISION_1"
], namespace=win32security)
