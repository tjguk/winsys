# -*- coding: iso-8859-1 -*-
r"""All security in windows is handled via Security Principals. These can
be a user (the most common case), a group of users, a computer, or something
else. Security principals are uniquely identified by their SID: a binary code
represented by a string S-a-b-cd-efg... where each of the segments represents
an aspect of the security authorities involved. (A computer, a domain etc.).
Certain of the SIDs are considered well-known such as the AuthenticatedUsers
account on each machine which will always have the same SID.

Most of the access to this module will be via the :func:`principal`
or :func:`me` functions. Although the module is designed to be used
standalone, it is imported directly into the :mod:`security` module's
namespace so its functionality can also be accessed from there.
"""
import os, sys
import contextlib
import socket

import ntsecuritycon
import pywintypes
import win32con
import win32security
import win32api
import win32cred
import win32event
import win32net
import win32netcon
import winerror

from winsys import constants, core, exc, utils
from winsys import _advapi32, dialogs

__all__ = ['LOGON', 'EXTENDED_NAME', 'x_accounts', 'principal', 'Principal', 'User', 'Group', 'me']

LOGON = constants.Constants.from_pattern ("LOGON32_*", namespace=win32security)
LOGON.doc ("Types of logon used by LogonUser and related APIs")
EXTENDED_NAME = constants.Constants.from_pattern ("Name*", namespace=win32con)
EXTENDED_NAME.doc ("Extended display formats for usernames")
WELL_KNOWN_SID = constants.Constants.from_pattern ("Win*Sid", namespace=win32security)
WELL_KNOWN_SID.doc ("Well-known SIDs common to all computers")
USER_PRIV = constants.Constants.from_list (["USER_PRIV_GUEST", "USER_PRIV_USER", "USER_PRIV_ADMIN"], pattern="USER_PRIV_*", namespace=win32netcon)
USER_PRIV.doc ("User-types for creating new users")
UF = constants.Constants.from_pattern ("UF_*", namespace=win32netcon)
UF.doc ("Flags for creating new users")
SID_NAME_USE = constants.Constants.from_pattern ("SidType*", namespace=ntsecuritycon)
SID_NAME_USE.doc ("Types of accounts for which SIDs exist")
FILTER = constants.Constants.from_pattern ("FILTER_*", namespace=win32netcon)
FILTER.doc ("Filters when enumerating users")

PySID = pywintypes.SIDType

class x_accounts (exc.x_winsys):
  "Base for all accounts-related exceptions"

WINERROR_MAP = {
  winerror.ERROR_NONE_MAPPED : exc.x_not_found
}
wrapped = exc.wrapper (WINERROR_MAP, x_accounts)

def _win32net_enum (win32_fn, system_or_domain):
  resume = 0
  while True:
    items, total, resume = wrapped (win32_fn, system_or_domain, 0, resume)
    for item in items:
      yield item
    if resume == 0: break

def principal (principal, cls=core.UNSET):
  r"""Factory function for the :class:`Principal` class. This is the most
  common way to create a :class:`Principal` object::

    from winsys import accounts
    service_account = accounts.principal (accounts.WELL_KNOWN_SID.Service)
    local_admin = accounts.principal ("Administrator")
    domain_users = accounts.principal (r"DOMAIN\Domain Users")

  :param principal: any of None, a :class:`Principal`, a `PySID`,
                    a :const:`WELL_KNOWN_SID` or a string
  :returns: a :class:`Principal` object corresponding to `principal`
  """
  cls = Principal if cls is core.UNSET else cls
  if principal is None:
    return None
  elif type (principal) == PySID:
    return cls.from_sid (principal)
  elif isinstance (principal, int):
    return cls.from_well_known (principal)
  elif isinstance (principal, cls):
    return principal
  else:
    return cls.from_string (unicode (principal))

def user (name):
  r"""If you know yo're after a user, use this. Particularly
  useful when a system user is defined as an alias type
  """
  return principal (name, cls=User)

def group (name):
  r"""If you know yo're after a group, use this. Particularly
  useful when a system group is defined as an alias type
  """
  return principal (name, cls=Group)

def local_group (name):
  r"""If you know yo're after a local group, use this.
  """
  return principal (name, cls=LocalGroup)

def global_group (name):
  r"""If you know yo're after a global group, use this.
  """
  return principal (name, cls=GlobalGroup)

def me ():
  r"""Convenience function for the common case of getting the
  logged-on user's account.
  """
  return Principal.me ()

_domain = None
def domain (system=None):
  global _domain
  if _domain is None:
    _domain = wrapped (win32net.NetWkstaGetInfo, system, 100)['langroup']
  return _domain

def domain_controller (domain=None):
  return wrapped (win32net.NetGetAnyDCName, None, domain)

def users (system=None):
  r"""Convenience function to yield each of the local users
  on a system.

  :param system: optional security authority
  :returns: yield :class:`User` objects
  """
  return iter (_LocalUsers (system))

class Principal (core._WinSysObject):
  r"""Object wrapping a Windows security principal, represented by a SID
  and, where possible, a name. :class:`Principal` compares and hashes
  by SID so can be sorted and used as a dictionary key, set element, etc.

  A :class:`Principal` is its own context manager, impersonating the
  corresponding user::

    from winsys import accounts
    with accounts.principal ("python"):
      print accounts.me ()

  Note, though, that this will prompt for a password using the
  Win32 password UI. To logon with a password, use the :meth:`impersonate`
  context-managed function. TODO: allow password to be set securely.
  """
  def __init__ (self, sid, system=None):
    """Initialise a Principal from and (optionally) a system name. The sid
    must be a PySID and the system name, if present must be a security
    authority, eg a machine or a domain.
    """
    core._WinSysObject.__init__ (self)
    self.sid = sid
    self.system = system
    try:
      self.name, self.domain, self.type = wrapped (win32security.LookupAccountSid, self.system, self.sid)
    except exc.x_not_found:
      self.name = str (self.sid)
      self.domain = self.type = None
    #~ if self.system is None:
      #~ self.system = domain_controller (self.domain)

  def __hash__ (self):
    return hash (str (self.sid))

  def __eq__ (self, other):
    return self.sid == principal (other).sid

  def __lt__ (self, other):
    return self.sid < principal (other).sid

  def pyobject (self):
    r"""Return the internal representation of this object.

    :returns: pywin32 SID
    """
    return self.sid

  def as_string (self):
    if self.domain:
      return r"%s\%s" % (self.domain, self.name)
    else:
      return self.name or str (self.sid)

  def dumped (self, level):
    return utils.dumped ("user: %s\nsid: %s" % (
      self.as_string (),
      wrapped (win32security.ConvertSidToStringSid, self.sid)
    ), level)

  def logon (self, password=core.UNSET, logon_type=core.UNSET):
    """Log on as an authenticated user, returning that
    user's token. This is used by security.impersonate
    which wraps the token in a Token object and manages
    its lifetime in a context.

    (EXPERIMENTAL) If no password is given, a UI pops up
    to ask for a password.

    :param password: the password for this account
    :param logon_type: one of the :const:`LOGON` values
    :returns: a pywin32 handle to a token
    """
    if logon_type is core.UNSET:
      logon_type = LOGON.LOGON_NETWORK
    else:
      logon_type = LOGON.constant (logon_type)
    if password is core.UNSET:
      password = dialogs.get_password (self.name, self.domain)
    hUser = wrapped (
      win32security.LogonUser,
      self.name,
      self.domain,
      password,
      logon_type,
      LOGON.PROVIDER_DEFAULT
    )
    return hUser

  @classmethod
  def from_string (cls, string, system=None):
    r"""Return a :class:`Principal` based on a name and a
    security authority. If `string` is blank, the logged-on user is assumed.

    :param string: name of an account in the form "domain\name". domain is optional so the simplest form is simply "name"
    :param system: name of a security authority (typically a machine or a domain)
    :returns: a :class:`Principal` object for `string`
    """
    if string == "":
      string = wrapped (win32api.GetUserNameEx, win32con.NameSamCompatible)
    sid, domain, type = wrapped (
      win32security.LookupAccountName,
      None if system is None else unicode (system),
      unicode (string)
    )
    cls = cls.SID_NAME_USE_MAP.get (type, cls)
    return cls (sid, None if system is None else unicode (system))

  @classmethod
  def from_sid (cls, sid, system=None):
    r"""Return a :class:`Principal` based on a sid and a security authority.

    :param sid: a PySID
    :param system_name: optional name of a security authority
    :returns: a :class:`Principal` object for `sid`
    """
    try:
      name, domain, type = wrapped (
        win32security.LookupAccountSid,
        None if system is None else unicode (system),
        sid
      )
    except exc.x_not_found:
      name = domain = type = core.UNSET
    cls = cls.SID_NAME_USE_MAP.get (type, cls)
    return cls (sid, None if system is None else unicode (system))

  @classmethod
  def from_well_known (cls, well_known, domain=None):
    r"""Return a :class:`Principal` based on one of the :const:`WELL_KNOWN_SID` values.

    :param well_known: one of the :const:`WELL_KNOWN_SID`
    :param domain: anything accepted by :func:`principal` and corresponding to a domain
    """
    return cls.from_sid (wrapped (win32security.CreateWellKnownSid, well_known, principal (domain)))

  @classmethod
  def me (cls):
    """Convenience factory method for the common case of referring to the
    logged-on user
    """
    return cls.from_string (wrapped (win32api.GetUserNameEx, EXTENDED_NAME.SamCompatible))

  @contextlib.contextmanager
  def impersonate (self, password=core.UNSET, logon_type=core.UNSET):
    """Context-managed function to impersonate this user and then
    revert::

      from winsys import accounts, security
      print accounts.me ()
      python = accounts.principal ("python")
      with python.impersonate ("Pa55w0rd"):
        print accounts.me ()
        open ("temp.txt", "w").close ()
      print accounts.me ()
      security.security ("temp.txt").owner == python

    Note that the :class:`Principal` class is also its own
    context manager but does not allow the password to be specified.

    :param password: password for this account
    :param logon_type: one of the :const:`LOGON` values
    """
    hLogon = self.logon (password, logon_type)
    wrapped (win32security.ImpersonateLoggedOnUser, hLogon)
    yield hLogon
    wrapped (win32security.RevertToSelf)

  def __enter__ (self):
    wrapped (win32security.ImpersonateLoggedOnUser, self.logon (logon_type=LOGON.LOGON_INTERACTIVE))

  def __exit__ (self, *exc_info):
    wrapped (win32security.RevertToSelf)

class User (Principal):

  @classmethod
  def create (cls, username, password, system=None):
    r"""Create a new user with `username` and `password`. Return
    a :class:`User` for the new user.

    :param username: username of the new user. Must not already exist on `system`
    :param password: password for the new user. Must meet security policy on `system`
    :param system: optional system name
    :returns: a :class:`User` for `username`
    """
    user_info = dict (
      name = username,
      password = password,
      priv = USER_PRIV.USER,
      home_dir = None,
      comment = None,
      flags = UF.SCRIPT,
      script_path = None
    )
    wrapped (win32net.NetUserAdd, system, 1, user_info)
    return cls.from_string (username, system)

  def delete (self):
    """Delete this user from `system`.

    :param system: optional security authority
    """
    wrapped (win32net.NetUserDel, self.system, self.name)

  def groups (self):
    """Yield the groups this user belongs to

    :param system: optional security authority
    """
    for group_name, attributes in wrapped (win32net.NetUserGetGroups, self.system, self.name):
      yield group (group_name)
    for group_name in wrapped (win32net.NetUserGetLocalGroups, self.system, self.name):
      yield group (group_name)

  def join (self, other_group):
    r"""Add this user to a group

    :param other_group: anything accepted by :func:`group`
    :returns: self
    """
    return group (other_group).add (self)

  def leave (self, other_group):
    r"""Remove this user from a group

    :param other_group: anything accepted by :func:`group`
    :returns: self
    """
    return group (other_group).remove (self)

  def runas (self, command_line, password=core.UNSET, load_profile=False):
    r"""Run a command logged on as this user

    :param command_line: command line to run, quoted as necessary
    :param password: password; if not supplied, standard Windows prompt
    :param with_profile: if True, HKEY_CURRENT_USER is loaded [False]
    """
    if not password:
      password = dialogs.get_password (self.name, self.domain)
    logon_flags = 0
    if load_profile: logon_flags |= _advapi32.LOGON_FLAGS.WITH_PROFILE
    process_info = _advapi32.CreateProcessWithLogonW (
      username=self.name,
      domain=self.domain,
      password=password,
      command_line=command_line,
      logon_flags=logon_flags
    )
    #
    # Wait for up to 20 secs
    #
    #~ if wrapped (win32event.WaitForInputIdle, process_info.hProcess, 10000) == win32event.WAIT_TIMEOUT:
      #~ raise x_accounts (errctx="runas", errmsg="runas process not created with 10 secs")

class Group (Principal):

  SID_NAME_USE_MAP = {}

  def __contains__ (self, member):
    r"""Crudely, iterate over the group's members until you hit `member`
    """
    member = principal (member)
    return any (member == m for m in self)

class GlobalGroup (Group):

  _enumerator = win32net.NetGroupEnum

  @classmethod
  def create (cls, groupname, domain=None):
    r"""Create a new group. Return a :class:`Group` for the new group.

    :param groupname: name of the new group. Must not already exist on `system`
    :param system: optional security authority
    :returns: a :class:`Group` for `groupname`
    """
    system = domain_controller (domain)
    wrapped (win32net.NetGroupAdd, system, 0, dict (name=groupname))
    return cls.from_string (groupname, system)

  def delete (self):
    r"""Delete this group from `system`.

    :param system: optional security authority
    """
    wrapped (win32net.NetGroupDel, self.system, self.name)

  def add (self, member):
    r"""Add a :class:`Principal` to this local group

    :param member: anything accepted by :func:`principal`
    :returns: :class:`Principal` for `member`
    """
    member = principal (member)
    wrapped (win32net.NetGroupAddUser, self.system, self.name, r"%s\%s" % (member.domain, member.name))
    return member

  def remove (self, member):
    r"""Remove a :class:`Principal` from this local group. The
    principal must already be a member of the group.

    :param member: anything accepted by :func:`principal`
    :returns: :class:`Principal` for `member`
    """
    member = principal (member)
    wrapped (win32net.NetGroupDelUser, self.system, self.name, r"%s\%s" % (member.domain, member.name))
    return member

  def __iter__ (self):
    r"""Yield the list of members of this group.

    :returns: yield a :class:`Principal` or subclass corresponding to each member
              of this group
    """
    resume = 0
    while True:
      members, total, resume = wrapped (win32net.NetGroupGetUsers, self.system, self.name, 1, resume)
      for member in members:
        yield principal (member['name'])
      if resume == 0: break

class LocalGroup (Group):

  @classmethod
  def create (cls, groupname, system=None):
    r"""Create a new group. Return a :class:`Group` for the new group.

    :param groupname: name of the new group. Must not already exist on `system`
    :param system: optional security authority
    :returns: a :class:`Group` for `groupname`
    """
    wrapped (win32net.NetLocalGroupAdd, system, 0, dict (name=groupname))
    return cls.from_string (groupname, system)

  def delete (self):
    r"""Delete this group from `system`.

    :param system: optional security authority
    """
    wrapped (win32net.NetLocalGroupDel, self.system, self.name)

  def add (self, member):
    r"""Add a :class:`Principal` to this local group

    :param member: anything accepted by :func:`principal`
    :returns: :class:`Principal` for `member`
    """
    member = principal (member)
    wrapped (win32net.NetLocalGroupAddMembers, self.system, self.name, 0, [dict (sid=member.sid)])
    return member

  def remove (self, member):
    r"""Remove a :class:`Principal` from this local group. The
    principal must already be a member of the group.

    :param member: anything accepted by :func:`principal`
    :returns: :class:`Principal` for `member`
    """
    member = principal (member)
    wrapped (win32net.NetLocalGroupDelMembers, self.system, self.name, ["%s\\%s" % (member.domain, member.name)])
    return member

  def __iter__ (self):
    r"""Yield the list of members of this group.

    :returns: yield a :class:`Principal` or subclass corresponding to each member
              of this group
    """
    resume = 0
    while True:
      members, total, resume = wrapped (win32net.NetLocalGroupGetMembers, self.system, self.name, resume)
      for member in members:
        yield principal (member['sid'])
      if resume == 0: break

Principal.SID_NAME_USE_MAP = {
  SID_NAME_USE.User : User,
  SID_NAME_USE.Group : Group,
  SID_NAME_USE.WellKnownGroup : Group
}

def local_groups (system=None):
  r"""Convenience function to yield each of the local users
  on a system.

  :param system: optional security authority
  :returns: yield :class:`LocalGroup` objects
  """
  for group in _win32net_enum (win32net.NetLocalGroupEnum, system):
    yield LocalGroup.from_string (group['name'])

def global_groups (domain=None):
  r"""Convenience function to yield each of the local users
  on a system.

  :param domain: optional security domain
  :returns: yield :class:`GlobalGroup` objects
  """
  for group in _win32net_enum (win32net.NetGroupEnum, domain_controller (domain)):
    yield GlobalGroup.from_string (group['name'])

class _LocalUsers (object):

  def __init__ (self, system=None):
    self.system = system

  def __iter__ (self):
    resume = 0
    while True:
      users, total, resume = wrapped (win32net.NetUserEnum, self.system, 0, FILTER.NORMAL_ACCOUNT, resume)
      for user in users:
        yield User.from_string (user['name'])
      if resume == 0: break

  def add (self, username, password):
    return User.create (username, password)

  def remove (self, local_user):
    return user (local_user).delete ()
