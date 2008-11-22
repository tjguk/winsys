# -*- coding: iso-8859-1 -*-
import pywintypes

class x_winsys (Exception):
  pass
  
class x_access_denied (x_winsys):
  pass
  
class x_not_found (x_winsys):
  pass

class x_invalid_handle (x_winsys):
  pass

def wrapper (winerror_map, default_exception=x_winsys):
  def _wrapped (function, *args, **kwargs):
    u"""Call a Windows API with parameters, and handle any
    exception raised either by mapping it to a module-specific
    one or by passing it back up the chain.
    """
    try:
      return function (*args, **kwargs)
    except pywintypes.error, (errno, errctx, errmsg):
      exception = winerror_map.get (errno, default_exception)
      raise exception (errmsg, errctx, errno)
    except (WindowsError, IOError), err:
      exception = winerror_map.get (err.errno, default_exception)
      if exception:
        raise exception (err.strerror, "", err.errno)
  return _wrapped
