import os

from . import utils
from ._fs_core import *

class FilePath (unicode):
  u"""Helper class which subclasses unicode, and can therefore be passed
  directly to API calls. It provides common operations on file paths:
  directory name, filename, parent directory &c.
  """
  def __new__ (meta, filepath, *args, **kwargs):
    is_dir = filepath[-1] in seps    
    filepath = utils.normalised (filepath) + (sep if is_dir else "")
    return unicode.__new__ (meta, filepath, *args, **kwargs)

  def __init__ (self, filepath, *args, **kwargs):
    u"""Break the filepath into its component parts, adding useful
    ones as instance attributes:
    
    FilePath.parts - a list of the components
    FilePath.root - the drive or UNC server/share always ending in a backslash
    FilePath.filename - final component (may be blank if the path looks like a directory)
    FilePath.name - same as filename unless empty in which case second-last component
    FilePath.dirname - all path components before the last
    FilePath.path - combination of volume and dirname
    FilePath.parent - combination of volume and all path components before second penultimate
    """
    self._parts = None
    self._root = None
    self._filename = None
    self._name = None
    self._dirname= None
    self._path = None
    self._parent = None
      
  def dump (self, level=0):
    print self.dumped (level=level)
  
  def dumped (self, level=0):
    output = []
    output.append (self)
    output.append (u"parts: %s" % self.parts)
    output.append (u"root: %s" % self.root)
    output.append (u"dirname: %s" % self.dirname)
    output.append (u"name: %s" % self.name)
    output.append (u"path: %s" % self.path)
    output.append (u"filename: %s" % self.filename)
    if self.parent:
      output.append (u"parent: %s" % self.parent)
    return utils.dumped (u"\n".join (output), level)
  
  def _get_parts (self):
    if self._parts is None:
      root = wrapped (win32file.GetVolumePathName, self)
      rest = self[len (root):]
      self._parts = [root] + rest.split (sep)
    return self._parts
  parts = property (_get_parts)
  
  def _get_root (self):
    if self._root is None:
      self._root = self.__class__ (self.parts[0])
    return self._root
  root = property (_get_root)
  
  def _get_filename (self):
    if self._filename is None:
      self._filename = self.parts[-1]
    return self._filename
  filename = property (_get_filename)
  
  def _get_dirname (self):
    if self._dirname is None:
      self._dirname = sep + sep.join (self.parts[1:-1])
    return self._dirname
  dirname = property (_get_dirname)
  
  def _get_path (self):
    if self._path is None:
      self._path = self.__class__ (self.root + self.dirname)
    return self._path
  path = property (_get_path)
  
  def _get_parent (self):
    if self._parent is None:
      parent_dir = [p for p in self.parts if p][:-1]
      if parent_dir:
        self._parent = self.__class__ (parent_dir[0] + sep.join (parent_dir[1:]))
      else:
        self._parent = None
    return self._parent
  parent = property (_get_parent)
  
  def _get_name (self):
    if self._name is None:
      self._name = self.parts[-1] or self.parts[-2]
    return self._name
  name = property (_get_name)
  
  def __getitem__ (self, index):
    return self.parts[index]
  
  def __add__ (self, other):
    return self.__class__ (os.path.join (unicode (self), unicode (other)))
  
  def relative_to (self, other):
    return utils.relative_to (self, unicode (other))
