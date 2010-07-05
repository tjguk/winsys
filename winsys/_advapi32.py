# -*- coding: iso-8859-1 -*-
"""Provide functions unavailable via pywin32 which reside in kernel32.dll
"""
import winerror
from ctypes.wintypes import *
from ctypes import windll, wintypes
import ctypes
import win32api
import win32file

from winsys import exc, constants

kernel32 = windll.kernel32
LOGON_FLAGS = constants.Constants.from_dict (dict (
  LOGON_WITH_PROFILE = 1,
  LOGON_NETCREDENTIALS_ONLY = 2
), pattern="LOGON_*")

class x_advapi32 (exc.x_winsys):
  pass

def error (exception, context="", message=""):
  errno = win32api.GetLastError ()
  message = message or win32api.FormatMessageW (errno)
  raise exception (errno, context, message)

TRUE  = 1
FALSE = 0

INVALID_HANDLE_VALUE = -1

#
# From a post to python-win32 by Mario Alejandro Vilas Jerez:
# http://mail.python.org/pipermail/python-win32/2009-June/009192.html
#

class PROCESS_INFORMATION(ctypes.Structure):
   _pack_   = 1
   _fields_ = [
       ('hProcess',    HANDLE),
       ('hThread',     HANDLE),
       ('dwProcessId', DWORD),
       ('dwThreadId',  DWORD),
   ]

class STARTUPINFO(ctypes.Structure):
   _pack_   = 1
   _fields_ = [
       ('cb',              DWORD),
       ('lpReserved',      DWORD),     # LPSTR
       ('lpDesktop',       LPSTR),
       ('lpTitle',         LPSTR),
       ('dwX',             DWORD),
       ('dwY',             DWORD),
       ('dwXSize',         DWORD),
       ('dwYSize',         DWORD),
       ('dwXCountChars',   DWORD),
       ('dwYCountChars',   DWORD),
       ('dwFillAttribute', DWORD),
       ('dwFlags',         DWORD),
       ('wShowWindow',     WORD),
       ('cbReserved2',     WORD),
       ('lpReserved2',     DWORD),     # LPBYTE
       ('hStdInput',       DWORD),
       ('hStdOutput',      DWORD),
       ('hStdError',       DWORD),
   ]

def CreateProcessWithLogonW (
  username = None,
  domain = None,
  password = None,
  logon_flags = 0,
  application_name = None,
  command_line = None,
  creation_flags = 0,
  environment = None,
  current_directory = None,
  startup_info = None
):
  if username: username = unicode (username)
  if domain: domain = unicode (domain)
  if password: password = unicode (password)
  if application_name: application_name = unicode (application_name)
  command_line = ctypes.create_unicode_buffer (command_line or "")
  if current_directory: current_directory = unicode (current_directory)
  if not startup_info:
    startup_info = STARTUPINFO ()
    startup_info.cb = ctypes.sizeof (STARTUPINFO)
    startup_info.lpReserved = 0
    startup_info.lpDesktop = 0
    startup_info.lpTitle = 0
    startup_info.dwFlags = 0
    startup_info.cbReserved2 = 0
    startup_info.lpReserved2 = 0

  process_information = PROCESS_INFORMATION ()
  process_information.hProcess = INVALID_HANDLE_VALUE
  process_information.hThread = INVALID_HANDLE_VALUE
  process_information.dwProcessId = 0
  process_information.dwThreadId = 0

  success = ctypes.windll.advapi32.CreateProcessWithLogonW (
    username,
    domain,
    password,
    logon_flags, application_name,
    ctypes.byref (command_line),
    creation_flags,
    environment,
    current_directory,
    ctypes.byref (startup_info),
    ctypes.byref (process_information)
  )
  if success:
    return process_information
  else:
    return error (x_advapi32, "CreateProcessWithLogonW")
