import os, sys
import re

import pythoncom
import win32com.client
from win32com.adsi import adsi, adsicon

from winsys import constants, core, exc, utils

"""Useful info from MSDN & elsewhere:

=   Equal to
~=  Approx. equal to
<=  Less than or equal to
>=  Greater than or equal to
&   AND
|   OR
!   NOT

:1.2.840.113556.1.4.803: bitwise AND
:1.2.840.113556.1.4.804: bitwise OR
:1.2.840.113556.1.4.1941: matching rule in chain

Special chars (must be substituted): *()\NUL/

"""

class x_active_directory (exc.x_winsys):
  "Base for all AD-related exceptions"

SEARCHPREF = constants.Constants.from_pattern (u"ADS_SEARCHPREF_*", namespace=adsicon)
SEARCHPREF.doc ("Preferences for searching AD")
SCOPE = constants.Constants.from_pattern (u"ADS_SCOPE_*", namespace=adsicon)
SCOPE.doc ("Scope for searching AD trees")

WINERROR_MAP = {
  adsicon.E_ADS_COLUMN_NOT_SET : exc.x_not_found,
  0x8000500D : AttributeError
}
wrapped = exc.wrapper (WINERROR_MAP, x_active_directory)

SEARCH_PREFERENCES = {
  SEARCHPREF.PAGESIZE : 1000,
  SEARCHPREF.SEARCH_SCOPE : SCOPE.SUBTREE,
}

class Result (dict):
  def __getattr__ (self, attr):
    return self[attr]

ESCAPED_CHARACTERS = dict ((special, r"\%02x" % ord (special)) for special in "*()\x00/")
def escaped (s):
  for original, escape in ESCAPED_CHARACTERS.items ():
    s = s.replace (original, escape)
  return s

class IADs (core._WinSysObject):

  def __init__ (self, obj, interface=adsi.IID_IADs):
    self._obj = wrapped (obj.QueryInterface, interface)

  def __getattr__ (self, attr):
    try:
      return getattr (self._obj, attr)
    except AttributeError:
      return wrapped (self._obj.Get, attr)

  def __getitem__ (self, item):
    return self.__class__.from_object (
      self._obj.QueryInterface (
        adsi.IID_IADsContainer
      ).GetObject (
        None,
        item
      )
    )

  def pyobject (self):
    return self._obj

  def as_string (self):
    return self._obj.ADsPath

  @classmethod
  def from_string (cls, moniker, username=None, password=None, interface=adsi.IID_IADs):
    return cls.from_object (
      adsi.ADsOpenObject (
        moniker,
        username, password,
        adsicon.ADS_SECURE_AUTHENTICATION | adsicon.ADS_SERVER_BIND | adsicon.ADS_FAST_BIND,
        interface
      )
    )

  @classmethod
  def from_object (cls, obj):
    klass = CLASS_MAP.get (obj.QueryInterface (adsi.IID_IADs).Class.lower (), cls)
    return klass (obj)

  def __iter__ (self):
    #
    # Try raise a meaningful error if you can't get an enumerator,
    # although it appears that you can enumerate just about anything,
    # including an IADsUser! It just returns an empty list.
    #
    try:
      enumerator = adsi.ADsBuildEnumerator (
        self._obj.QueryInterface (
          adsi.IID_IADsContainer
        )
      )
    except:
      raise TypeError ("%r is not iterable" % self)

    while True:
      item = adsi.ADsEnumerateNext (enumerator, 1)
      if item:
        yield IADs.from_object (item[0])
      else:
        break

  def walk (self, depthfirst=False):
    ur"""Mimic os.walk, iterating over each container and the items within
    in. Each iteration yields:

      container, (iterator for items)

    Since all AD items are effectively containers, don't bother producing
    a separate iterator for them.

    :param depthfirst: Whether to use breadth-first (the default) or depth-first traversal
    :returns: yield container, (iterator for items)
    """
    top = self
    containers, items = [], []
    for item in self:
      if isinstance (f, Dir):
        dirs.append (f)
      else:
        nondirs.append (f)

    if not depthfirst: yield top, dirs, nondirs
    for d in dirs:
      for x in d.walk (depthfirst=depthfirst, ignore_access_errors=ignore_access_errors):
        yield x
    if depthfirst: yield top, dirs, nondirs


class IADsOU (IADs):

  def __init__ (self, obj):
    IADs.__init__ (self, obj)

class IADsUser (IADs):

  def __init__ (self, obj):
    IADs.__init__ (self, obj)

class IADsGroup (IADs):

  def __init__ (self, obj):
    IADs.__init__ (self, obj)

class GC (IADs):

  def __iter__ (self):
    for domain in IADs.__iter__ (self):
      print domain
      yield ad ("LDAP://" + domain.Name)

def ad (obj=core.UNSET, username=None, password=None, interface=adsi.IID_IADs):

  if obj is core.UNSET:
    return IADs.from_string (ldap_moniker (username=username, password=password), username, password)
  elif obj is None:
    return None
  elif isinstance (obj, IADs):
    return obj
  elif isinstance (obj, basestring):
    moniker = obj
    if not moniker.upper ().startswith ("LDAP://"):
      moniker = "LDAP://" + moniker
    return IADs.from_string (moniker, username, password, interface)
  else:
    return IADs.from_object (obj)

def ldap_moniker (root=None, server=None, username=None, password=None):
  #
  # FIXME: Need to allow for GC/WinNT monikers
  #
  if root is None:
    root = adsi.ADsOpenObject (
      ldap_moniker ("rootDSE", server),
      username, password,
      adsicon.ADS_SECURE_AUTHENTICATION | adsicon.ADS_SERVER_BIND | adsicon.ADS_FAST_BIND,
      adsi.IID_IADs
    ).Get ("defaultNamingContext")
  prefix, rest = re.match ("(\w+://)?(.*)", root).groups ()
  if not prefix:
    prefix = "LDAP://"
  if server:
    return "%s%s/%s" % (prefix, server, root)
  else:
    return "%s%s" % (prefix, root)

def search (filter, columns=["distinguishedName"], root=None, server=None, username=None, password=None):

  def get_column_value (hSearch, column):
    #
    # FIXME: Need a more general-purpose way of determining which
    # fields are indeed lists. Either a factory function or a
    # peek at the schema.
    #
    CONVERT_TO_LIST = set (['memberOf', "member"])
    try:
      column_name, column_type, column_values = directory_search.GetColumn (hSearch, column)
      if column_name in CONVERT_TO_LIST:
        return list (value for value, type in column_values)
      else:
        for value, type in column_values:
          return value
    except adsi.error, details:
      if details[0] == adsicon.E_ADS_COLUMN_NOT_SET:
        return None
      else:
        raise

  pythoncom.CoInitialize ()
  try:
    directory_search = adsi.ADsOpenObject (
      ldap_moniker (root, server, username, password),
      username, password,
      adsicon.ADS_SECURE_AUTHENTICATION | adsicon.ADS_SERVER_BIND | adsicon.ADS_FAST_BIND,
      adsi.IID_IDirectorySearch
    )
    directory_search.SetSearchPreference ([(k, (v,)) for k, v in SEARCH_PREFERENCES.items ()])

    hSearch = directory_search.ExecuteSearch (filter, columns)
    try:
      hResult = directory_search.GetFirstRow (hSearch)
      while hResult == 0:
        yield Result ((column, get_column_value (hSearch, column)) for column in columns)
        hResult = directory_search.GetNextRow (hSearch)
    finally:
      directory_search.AbandonSearch (hSearch)
      directory_search.CloseSearchHandle (hSearch)

  finally:
    pythoncom.CoUninitialize ()

def _and (*args):
  return "(&%s)" % "".join ("(%s)" % s for s in args)

def _or (*args):
  return "(|%s)" % "".join ("(%s)" % s for s in args)

def find_user (name, root_path=None, server=None, username=None, password=None, columns=["*"]):
  name = escaped (name)
  for user in search (
    _and (
      "objectClass=user",
      "objectCategory=person",
      _or (
        "sAMAccountName=" + name,
        "displayName=" + name,
        "cn=" + name
      )
    ),
    ["distinguishedName", "sAMAccountName", "displayName", "memberOf", "physicalDeliveryOfficeName", "title", "telephoneNumber", "homePhone"],
    root_path,
    server,
    username,
    password
  ):
    return user

def find_group (name, root_path=None, server=None, username=None, password=None, columns=["*"]):
  name = escaped (name)
  for group in search (
    filter=_and (
      "objectClass=group",
      _or (
        "sAMAccountName=" + name,
        "displayName=" + name,
        "cn=" + name
      )
    ),
    columns=columns,
    root=root_path, server=server, username=username, password=password
  ):
    return group

def find_active_users (root=None, server=None, username=None, password=None, columns=["*"]):
  return search (
    filter=_and (
      "objectClass=user",
      "objectCategory=person",
      "!memberOf=CN=non intranet,OU=IT Other,OU=IT,OU=Camden,DC=gb,DC=vo,DC=local",
      "!userAccountControl:1.2.840.113556.1.4.803:=2",
      "displayName=*"
    ),
    columns=columns,
    root=None, server=None, username=None, password=None
  )

def find_all_users (root=None, server=None, username=None, password=None):
  for user in search (
    filter=_and (
      "objectClass=user",
      "objectCategory=person",
      "displayName=*"
    ),
    columns=["distinguishedName"],
    root=None, server=None, username=None, password=None
  ):
    yield ad (user.distinguishedName)

def find_all_namespaces ():
  for i in win32com.client.GetObject ("ADs:"):
    yield i.ADsPath

def gc ():
  return ad ("GC:")

CLASS_MAP = {
  "organizationalUnit" : IADsOU,
  "user" : IADsUser,
  "group" : IADsGroup,
}
