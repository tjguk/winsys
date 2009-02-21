"""Set up a windows box so that the version of Python running
this script is considered to be the active one. This involves:

1) Adding it to the system or user PATH, removing all other paths
which contain a Python executable.

2) Associating .py files with it so that double-clicking or typing
the .py file name alone will run the right version.

3) Adding it as an AppPath so that Start > Run > python will run
this version.

4) Establishing it as a drop handler so that dragging a file over
a .py file will run the .py file with this version of Python, passing
the dropped file as sys.argv[1].

5) Finally, sending a broadcast message to all windows to indicate that
the environment has changed and that they ought to refetch their copy.
"""
import os, sys
import _winreg
import warnings
try:
  import ctypes
  from ctypes import wintypes
except ImportError:
  warnings.warn ("ctypes not found; PATH changes will not be visible until next login")
  ctypes = wintypes = None

EXECUTABLE = os.path.abspath (sys.executable)
PYTHON_DIRNAME = os.path.dirname (EXECUTABLE)

try:
  enumerate
except NameError:
  def enumerate (sequence):
    return [(i, sequence[i]) for i in range (len (sequence))]

def find_python_exes (paths):
  return [i for (i, p) in enumerate (paths) if os.path.exists (os.path.join (p, "python.exe"))]

if ctypes:
  def expand_environment_strings (path):
    n_chars = 2 * len (path)
    returned_string = ctypes.create_string_buffer (n_chars)
    ctypes.windll.kernel32.ExpandEnvironmentStringsA (
      path, returned_string, n_chars
    )
    return returned_string.value
else:
  def expand_environment_strings (path):
    return path
  
def add_to_path (user_or_system):
  """Note that, uniquely, Windows creates an effective path by combining 
  system & user paths in that order. At the end of this function, there 
  should be exactly one version of Python referenced in the combined path.
  If you're updating the system, you'll certainly have access to the user
  path; if you're updating the user path you may not have access to adjust
  the system path. An attempt is made to adjust it, but an access denied
  error will be propagated if this fails.
  """
  USER_REG = r""
  SYSTEM_REG = r"SYSTEM\CurrentControlSet\Control\Session Manager"
  user_key = _winreg.CreateKey (_winreg.HKEY_CURRENT_USER, USER_REG)
  system_key = _winreg.CreateKey (_winreg.HKEY_LOCAL_MACHINE, SYSTEM_REG)
    
  old_user_path = _winreg.QueryValueEx (_winreg.CreateKey (user_key, "Environment"), "PATH")[0]
  user_paths = expand_environment_strings (old_user_path.encode ("cp1252")).split (";")
  old_system_path = _winreg.QueryValueEx (_winreg.CreateKey (system_key, "Environment"), "PATH")[0]
  system_paths = expand_environment_strings (old_system_path.encode ("cp1252")).split (";")
  
  system_python_exes = find_python_exes (system_paths)
  user_python_exes = find_python_exes (user_paths)

  #
  # Find the current user path, remove any existing Python-related paths,
  # add the current python.exe/scripts path to the end and write it
  # back to the registry.
  #
  if user_or_system == "system":
    for python_path in [system_paths[i] for i in system_python_exes]:
      system_paths = [p for p in system_paths if not p.startswith (python_path)]
    system_paths.append (PYTHON_DIRNAME)
    system_paths.append (os.path.join (PYTHON_DIRNAME, "scripts"))
    new_system_path = ";".join (system_paths)
    if new_system_path <> old_system_path:
      _winreg.SetValueEx (_winreg.CreateKey (system_key, "Environment"), "PATH", 0, _winreg.REG_EXPAND_SZ, ";".join (system_paths))
      _winreg.SetValueEx (_winreg.CreateKey (system_key, "Environment"), "OLDPATH", 0, _winreg.REG_EXPAND_SZ, old_system_path)

  for python_path in [user_paths[i] for i in user_python_exes]:
    user_paths = [u for u in user_paths if not u.startswith (python_path)]
  if user_or_system == "user":
    user_paths.append (PYTHON_DIRNAME)
    user_paths.append (os.path.join (PYTHON_DIRNAME, "scripts"))
  new_user_path = ";".join (user_paths)
  if new_user_path <> old_user_path:
    _winreg.SetValueEx (_winreg.CreateKey (user_key, "Environment"), "OLDPATH", 0, _winreg.REG_EXPAND_SZ, old_user_path)
    _winreg.SetValueEx (_winreg.CreateKey (user_key, "Environment"), "PATH", 0, _winreg.REG_EXPAND_SZ, new_user_path)


def add_association (user_or_system):
  if user_or_system == "user":
    root = _winreg.HKEY_CURRENT_USER
  else:
    root = _winreg.HKEY_LOCAL_MACHINE
  
  _winreg.SetValueEx (
    _winreg.CreateKey (
      root,
      r"Software\Classes\.py"
    ), "", 0, _winreg.REG_SZ, "Python.File"
  )
  _winreg.SetValueEx (
    _winreg.CreateKey (
      root,
      r"Software\Classes\Python.File\shell\open\command"
    ), "", 0, _winreg.REG_SZ, '"%s" "%%1" %%*' % EXECUTABLE
  )

def add_drop_handler (user_or_system):
  pass

def add_apppath (user_or_system):
  if user_or_system == "user":
    root = _winreg.HKEY_CURRENT_USER
  else:
    root = _winreg.HKEY_LOCAL_MACHINE
  
  _winreg.SetValueEx (
    _winreg.CreateKey (
      root,
      r"Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe"
    ),
    "",
    0,
    _winreg.REG_SZ,
    EXECUTABLE
  )

def add_pathext ():
  """PATHEXT determines which file types are considered "executable",
  ie can be run simply by typing their name without an extension into
  a command prompt. As opposed to PATH, where the user value is appended
  to the system, a user PATHEXT overrides a system one. Therefore only
  make this change as system.
  """
  PYTHON_PATHEXTS = ['.py', '.pyc', '.pyw', '.pys', '.pyo']
  SYSTEM_REG = r"SYSTEM\CurrentControlSet\Control\Session Manager"
  system_key = _winreg.CreateKey (_winreg.HKEY_LOCAL_MACHINE, SYSTEM_REG)
    
  old_pathexts = _winreg.QueryValueEx (_winreg.CreateKey (system_key, "Environment"), "PATHEXT")[0]
  _winreg.SetValueEx (system_key, "OLD_PATHEXT", 0, _winreg.REG_SZ, old_pathexts)
  
  print "old_pathexts", old_pathexts
  pathexts = [p for p in old_pathexts.lower ().split (";") if p not in PYTHON_PATHEXTS] + PYTHON_PATHEXTS
  print "pathexts", pathexts
  print ";".join (pathexts)
  _winreg.SetValueEx (system_key, "PATHEXT", 0, _winreg.REG_SZ, ";".join (pathexts))

if ctypes and wintypes:
  def notify_changes ():
    HWND_BROADCAST = 65535
    WM_SETTINGCHANGE = 26
    SMTO_ABORTIFHUNG = 2  
    result = wintypes.DWORD ()
    ctypes.windll.user32.SendMessageTimeoutA (
      HWND_BROADCAST,
      WM_SETTINGCHANGE,
      0,
      "Environment",
      SMTO_ABORTIFHUNG,
      2000,
      ctypes.byref (result)
    )
else:
  def notify_changes ():
    pass

if __name__ == '__main__':
  if len (sys.argv) > 1:
    user_or_system = sys.argv[1].lower ()
  else:
    user_or_system = "system"
  
  add_to_path (user_or_system)
  add_association (user_or_system)
  add_apppath (user_or_system)
  add_drop_handler (user_or_system)
  if user_or_system == "system":
    add_pathext ()
  notify_changes ()
