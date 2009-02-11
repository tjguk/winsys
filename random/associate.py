import os, sys
import ctypes
from ctypes import wintypes
import _winreg

EXECUTABLE = os.path.abspath (sys.executable)
PYTHON_DIRNAME = os.path.dirname (EXECUTABLE)

def find_python_exes (paths):
  return [i for (i, p) in enumerate (paths) if os.path.exists (os.path.join (p, "python.exe"))]

def add_to_path ():
  system_paths = _winreg.ExpandEnvironmentStrings (
    _winreg.QueryValueEx (
      _winreg.CreateKey (
        _winreg.HKEY_LOCAL_MACHINE, 
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
      ), 
      "PATH"
    )[0]
  ).split (";")
  python_exes = find_python_exes (system_paths)
  if python_exes:
    raise RuntimeError ("python.exe found in system paths: %s" % ", ".join (system_paths[i] for i in python_exes))

  #
  # Find the current user path, remove any existing Python-related paths,
  # add the current python.exe/scripts path to the end and write it
  # back to the registry.
  #
  user_environment_key = _winreg.CreateKey (_winreg.HKEY_CURRENT_USER, r"Environment")
  user_paths = _winreg.ExpandEnvironmentStrings (
    _winreg.QueryValueEx (user_environment_key, "PATH")[0]
  ).split (";")
  for python_path in set (user_paths[i] for i in find_python_exes (user_paths)):
    user_paths = [u for u in user_paths if not u.startswith (python_path)]
  user_paths.append (PYTHON_DIRNAME)
  user_paths.append (os.path.join (PYTHON_DIRNAME, "scripts"))
  _winreg.SetValueEx (user_environment_key, "PATH", 0, _winreg.REG_EXPAND_SZ, ";".join (user_paths))
  
def add_association ():
  _winreg.SetValueEx (
    _winreg.CreateKey (
      _winreg.HKEY_CLASSES_ROOT, 
      ".py"
    ), "", 0, _winreg.REG_SZ, "Python.File"
  )
  _winreg.SetValueEx (
    _winreg.CreateKey (
      _winreg.HKEY_CLASSES_ROOT, 
      r"Python.File\shell\open\command"
    ), "", 0, _winreg.REG_SZ, '"%s" "%%1" %%*' % EXECUTABLE
  )
  
def add_apppath ():
  _winreg.SetValueEx (
    _winreg.CreateKey (
      _winreg.HKEY_CURRENT_USER,
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
  to the system, a user PATHEXT overrides a system one. Therefore, copy
  the system one over.
  """
  pass

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

if __name__ == '__main__':
  add_to_path ()
  add_association ()
  add_apppath ()
  add_pathext ()
  notify_changes ()
