# -*- coding: iso-8859-1 -*-
ur"""Each process has an environment block (which may be empty). It
consists of a set of key-value pairs, each of which is a string.
The value string may be formed partly or wholly from other environment
variables using the %envvar% notation. By default, this module will
reinterpret those embedded variables but this can be overriden.

The process environment is derived on startup from a combination
of the system environment variables and the user's environment
variable, some of which are generated automatically by the
system to reflect the user's profile location and home drive etc.

All three environments are available as a dictalike class whose
interface matches the :class:`Env` base class. Each environment
object quacks like a dict in respect of item access, :meth:`Env.get`,
:meth:`Env.keys`, :meth:`Env.items` and :meth:`Env.update` methods
and the system and user objects supply an additional :meth:`Persistent.broadcast`
method which sends a message to top-level windows, such as the shell, to
indicate that the environment has changed.
"""
import os, sys
import win32api
import win32profile
import win32gui
import win32con
import winerror

from winsys import core, exc, utils, registry

class x_environment (exc.x_winsys):
  "Base exception for all env exceptions"

WINERROR_MAP = {
  winerror.ERROR_ENVVAR_NOT_FOUND : exc.x_not_found,
}
wrapped = exc.wrapper (WINERROR_MAP, x_environment)

class _DelimitedText (list):
  ur""""Helper class for values such as PATH and PATHEXT which are
  consistently semicolon-delimited text but which can helpfully
  be treated as a list of individual values. Subclasseed from
  list, it keeps track of the delimited list while exposing
  the more familiar Pythonesque list interface.
  """

  def __init__ (self, env, key, delimiter=";", initialiser=None):
    super (_DelimitedText, self).__init__ (env[key].split (delimiter) if initialiser is None else initialiser)
    self.env = env
    self.key = key
    self.delimiter = unicode (delimiter)

  def _update (self):
    self.env[self.key] = self.delimiter.join (self)

  def __delitem__ (self, *args):
    super (_DelimitedText, self).__delitem__ (*args)
    self._update ()

  def __delslice__ (self, *args):
    super (_DelimitedText, self).__delslice__ (*args)
    self._update ()

  def __iadd__ (self, iterator):
    super (_DelimitedText, self).__iadd__ (self.munge_item (unicode (i)) for i in iterator)
    self._update ()
    return self

  def __setitem__ (self, index, item):
    super (_DelimitedText, self).__setitem__ (index, self.munge_item (unicode (item)))
    self._update ()

  def __setslice__ (self, index0, index1, iterator):
    super (_DelimitedText, self).__setitem__ (index0, index1, (self.munge_item (unicode (item)) for item in iterator))
    self._update ()

  def append (self, item):
    super (_DelimitedText, self).append (self.munge_item (unicode (item)))
    self._update ()

  def extend (self, item):
    super (_DelimitedText, self).extend (self.munge_item (unicode (item)))
    self._update ()

  def insert (self, index, item):
    super (_DelimitedText, self).insert (index, self.munge_item (unicode (object)))
    self._update ()

  def pop (self, index=-1):
    result = super (_DelimitedText, self).pop (index)
    self._update ()
    return result

  def remove (self, item):
    super (_DelimitedText, self).remove (self.munge_item (unicode (item)))
    self._update ()

  def reverse (self):
    super (_DelimitedText, self).reverse ()
    self._update ()

  def sort (self):
    super (_DelimitedText, self).sort ()
    self._update ()

  def munge_item (self, item):
    return item

class _DelimitedPath (_DelimitedText):
  ur"""Subclass of delimited text to ensure that valid filesystem paths
  are stored in the env var
  """

  def munge_item (self, item):
    return os.path.normpath (item).rstrip ("\\")

class Env (core._WinSysObject):
  ur"""Semi-abstract base class for all environment classes. Outlines
  a dict-like interface which relies on subclasses to implement simple
  :meth:`_get` and :meth:`_items` methods.
  """
  def __getitem__ (self, item):
    ur"""Get environment strings like dictionary items::

      from winsys import environment

      print environment.system ()['windir']
    """
    raise NotImplementedError

  def __setitem__ (self, item, value):
    ur"""Set environment strings like dictionary items::

      from winsys import environment

      environment.user ()['winsys'] = 'TEST'
    """
    raise NotImplementedError

  def __delitem__ (self, item):
    ur"""Remove an item from the environment::

      from winsys import environment

      del environment.process ()['winsys']
    """
    raise NotImplementedError

  def __repr__ (self):
    return repr (dict (self.iteritems ()))

  def dumped (self, level):
    return utils.dumped_dict (dict (self.iteritems ()), level)

  def keys (self):
    """Yield environment variable names
    """
    raise NotImplementedError

  def items (self, expand=True):
    """Yield key-value pairs of environment variables

    :param expand: whether to expand embedded environment variables [True]
    """
    return (
      (k, self.expand (v) if expand else v)
        for k, v
        in self._items ()
    )

  def _get_path (self):
    if self.get ("PATH"):
      return _DelimitedPath (self, "PATH")
    else:
      return _DelimitedPath (self, "PATH", initialiser=[])
  def _set_path (self, iterator):
    self['PATH'] = ";".join (_DelimitedPath (self, "PATH", initialiser=iterator))
  def _del_path (self):
    del self['PATH']
  path = property (_get_path, _set_path, _del_path)

  def get (self, item, default=None, expand=True):
    """Return an environment value if it exists, otherwise
    `[default]`. This is the only way to get an unexpanded
    environment value by setting `expand` to False.

    :param item: name of an environment variable
    :param default: value to return if no such environment variable exists.
                    This default is expanded if `expand` is True.
    :param expand: whether to expand embedded environment variables [True]
    """
    try:
      v = self._get (item)
    except KeyError:
      return default
    else:
      return self.expand (v) if expand else v

  def update (self, dict_initialiser):
    """Update this environment from a dict-like object, typically
    another environment::

      from winsys import environment

      penv = environment.process ()
      penv.update (environment.system ())
    """
    for k, v in dict (dict_initialiser).iteritems ():
      self[k] = v

  @staticmethod
  def expand (item):
    """Return a version of `item` with internal environment variables
    expanded to their corresponding value. This is done automatically
    by the functions in this class unless you specify `expand=False`.
    """
    return wrapped (win32api.ExpandEnvironmentStrings, unicode (item))

class Process (Env):
  """The environment corresponding to the current process. This is visible
  only to the current process and its children (assuming the environment block
  is passed). Any changes you make here apply only for the lifetime of this
  process and do not affect the permanent user or system environment. See
  the :func:`system` and :func:`user` functions for ways to update the
  environment permanently.
  """
  def __init__ (self):
    super (Process, self).__init__ ()

  def keys (self):
    return (k for k in wrapped (win32profile.GetEnvironmentStrings).iterkeys ())

  def _items (self):
    return (item for item in wrapped (win32profile.GetEnvironmentStrings).iteritems ())

  def _get (self, item):
    return wrapped (win32api.GetEnvironmentVariable, item)

  def __getitem__ (self, item):
    value = self._get (item)
    if value is None:
      raise KeyError
    else:
      return unicode (value)

  def __setitem__ (self, item, value):
    if value is None:
      wrapped (win32api.SetEnvironmentVariable, item, None)
    else:
      wrapped (win32api.SetEnvironmentVariable, item, unicode (value))

  def __delitem__ (self, item):
    wrapped (win32api.SetEnvironmentVariable, item, None)

class Persistent (Env):
  ur"""Represent persistent (registry-based) environment variables. These
  are held at system and at user level, the latter overriding the former
  when an process environment is put together. Don't instantiate this
  class directly: use the :func:`user` and :func:`system` functions.
  """

  @staticmethod
  def broadcast (timeout_ms=2000):
    ur"""Broadcast a message to all top-level windows informing them that
    an environment change has occurred. The message must be sent, not posted,
    and times out after `timeout_ms` ms since some top-level windows handle this
    badly. NB This is a static method.
    """
    win32gui.SendMessageTimeout (
      win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE,
      0, "Environment",
      win32con.SMTO_ABORTIFHUNG, timeout_ms
    )

  def __init__ (self, root):
    super (Persistent, self).__init__ ()
    self.registry = registry.registry (root)

  def _get (self, item):
    try:
      return unicode (self.registry.get_value (item))
    except exc.x_not_found:
      raise KeyError

  def keys (self):
    return (name for name, value in self.registry.itervalues ())

  def _items (self):
    return list (self.registry.itervalues ())

  def __getitem__ (self, item):
    value = self._get (item)
    if value is None:
      raise KeyError
    else:
      return value

  def __setitem__ (self, item, value):
    self.registry.set_value (item, unicode (value))

  def __delitem__ (self, item):
    del self.registry[item]

def process ():
  ur"""Return a dict-like object representing the environment block of the
  current process.
  """
  return Process ()

def system (machine=None):
  ur"""Return a dict-like object representing the system-level persistent
  environment variables, optionally selecting a different machine.

  :param machine: name or address of a different machine whose system
                  environment is to be represented.
  """
  ROOT = r"HKLM\System\CurrentControlSet\Control\Session Manager\Environment"
  if machine:
    root = r"\\%s\%s" % (machine, ROOT)
  else:
    root = ROOT
  return Persistent (root)

def user ():
  ur"""Return a dict-like object representing the user-level persistent
  environment for the logged-on user.

  TODO: include alternate user functionality via logon token
  """
  return Persistent (ur"HKCU\Environment")

