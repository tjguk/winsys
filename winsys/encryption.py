# -*- coding: utf-8 -*-
"""
"""
from __future__ import unicode_literals

import os, sys
import marshal

import win32crypt

from winsys._compat import *
from winsys import constants, core, exc, utils

class x_encryption(exc.x_winsys):
    "Base exception for all env exceptions"

PROTECT = constants.Constants.from_pattern("CRYPTPROTECT_*", namespace=win32crypt)

WINERROR_MAP = {
    ## winerror.ERROR_ENVVAR_NOT_FOUND : exc.x_not_found,
}
wrapped = exc.wrapper(WINERROR_MAP, x_encryption)

def encrypted(obj, password=None, name=None, is_user=True):
    """Encrypt any Python object

    :param obj: any Python object which can be marshalled
    :param password: optional string to act as entropy
    :param name: optional name
    :param is_user: optionally indicates whether user or machine
    :returns: a byte string containing an encrypted version of `data`
    """
    flags = 0
    if not is_user:
        flags |= PROTECT.LOCAL_MACHINE
    data = marshal.dumps(obj)
    return wrapped(win32crypt.CryptProtectData, data, name, password, None, None, flags)

def decrypted(data, password=None, is_user=True):
    """Decrypt to any Python object

    :param data: a byte string previously encrypted using :func:`encrypted`
    :param passowrd: the optional password originally used to encrypt
    :param is_user: optionally indicate whether user or machine
    :returns: a Python object
    """
    flags = 0
    if not is_user:
        flags |= PROTECT.LOCAL_MACHINE
    name, data = wrapped(win32crypt.CryptUnprotectData, data, password, None, None, flags)
    return marshal.loads(data)
