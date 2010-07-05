import win32security

from winsys import accounts, constants, core, exc, utils

__all__ = ['LogonSession', 'LSA', 'x_lsa']

class x_lsa (exc.x_winsys):
  "Base for all LSA-related exceptions"

WINERROR_MAP = {
}
wrapped = exc.wrapper (WINERROR_MAP, x_lsa)

def principal (account):
  try:
    return accounts.principal (account)
  except exc.x_not_found:
    return "<unknown>"

class LogonSession (core._WinSysObject):

  _MAP = {
    "UserName" : principal,
    "Sid" : principal,
    "LogonTime" : utils.from_pytime
  }

  def __init__ (self, session_id):
    core._WinSysObject.__init__ (self)
    self._session_id = session_id
    self._session_info = dict (session_id = self._session_id)
    for k, v in wrapped (win32security.LsaGetLogonSessionData, session_id).items ():
      mapper = self._MAP.get (k)
      if mapper: v = mapper (v)
      self._session_info[k] = v

  def __getattr__ (self, attr):
    return self._session_info[attr]

  def __dir__ (self):
    return self._session_info.keys ()

  def as_string (self):
    return "Logon Session %(session_id)s for %(UserName)s" % self._session_info

  def dumped (self, level):
    output = []
    output.append ("session_id: %s" % self._session_id)
    output.append ("UserName: %s" % self.UserName)
    output.append ("Sid: %s" % (self.Sid.sid if self.Sid else None))
    output.append ("LogonTime: %s" % self.LogonTime)
    return utils.dumped ("\n".join (output), level)

class LSA (core._WinSysObject):

  def __init__ (self, system_name=None):
    core._WinSysObject.__init__ (self)
    self._lsa = wrapped (win32security.LsaOpenPolicy, system_name, 0)

  @staticmethod
  def logon_sessions ():
    for session_id in wrapped (win32security.LsaEnumerateLogonSessions):
      yield LogonSession (session_id)

if __name__ == '__main__':
  for logon_session in LSA.logon_sessions ():
    logon_session.dump ()