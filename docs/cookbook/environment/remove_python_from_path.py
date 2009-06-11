from winsys import registry, environment

def munge_path (env, python_paths):
  #env['PATH'] = 
  print ";".join (
    p for p in env['PATH'].split (";") if not any (
      p.lower ().startswith (py) for py in python_paths
    )
  )

py = registry.registry (r"hklm\software\python\pythoncore")
py_paths = set (version.InstallPath.get_value ("").rstrip ("\\").lower () for version in py)
py = registry.registry (r"hkcu\software\python\pythoncore")
py_paths.update (version.InstallPath.get_value ("").rstrip ("\\").lower () for version in py)

munge_path (environment.user (), py_paths)
munge_path (environment.system (), py_paths)
