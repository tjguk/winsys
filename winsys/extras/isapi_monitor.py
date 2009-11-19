import win32traceutil
import monitor_directory
import isapi_wsgi

def __ExtensionFactory__ ():
  return isapi_wsgi.ISAPISimpleHandler (monitor_directory.App ())
    
def set_auth (params, options, target_dir):
  #
  # Make sure directory authentication is:
  #   - Anonymous
  #   - NTLM
  #
  target_dir.AuthFlags = 5
  target_dir.SetInfo ()
    
if __name__ == '__main__':
  from isapi.install import *
  params = ISAPIParameters ()
  sm = [
    ScriptMapParams (Extension="*", Flags=0)
  ]
  vd = VirtualDirParameters (
    Name="monitor",
    Description = "Monitor Directory",
    ScriptMaps = sm,
    ScriptMapUpdate = "replace",
    PostInstall=set_auth
  )
  params.VirtualDirs = [vd]
  HandleCommandLine (params)
