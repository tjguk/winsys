# -*- coding: iso-8859-1 -*-
import os, sys
import re
import struct

from win32file import *
import winioctlcon

FORMATS = {
  u"DWORDLONG" : "Q",
  u"USN" : "q",
  u"DWORD" : "L"
}

def parse_structure (structure):
  return [(item, FORMATS[size]) for (size, item) in re.findall (r"([A-Z]+)\s(\w+);", structure)]

class Data (object):
  
  STRUCTURE = []
  
  def __init__ (self, *items):
    self._items = dict (zip (self.items (), items))
    
  def __getattr__ (self, attr):
    try:
      return self._items[attr]
    except KeyError:
      raise AttributeError, attr
    
  def __str__ (self):
    return self.to_data ()

  @classmethod
  def size (cls):
    return struct.calcsize (cls.format ())
  
  @classmethod
  def items (cls):
    return (s[0] for s in cls.STRUCTURE)
      
  @classmethod
  def format (cls):
    return "".join (s[1] for s in cls.STRUCTURE)
  
  @classmethod
  def from_data (cls, data):
    return cls (*struct.unpack (cls.format (), data))
    
  def to_data (self):
    return struct.pack (self.format (), *(self._items[item] for item in self.items ()))
      
  def dump (self):
    print u"{\n  %s\n}" % "\n  ".join ("%s : %s" % (k, v) for (k, v) in self._items.items ())

USN_JOURNAL_DATA_STRUCT = u"""
  DWORDLONG UsnJournalID;  
  USN FirstUsn;  
  USN NextUsn;  
  USN LowestValidUsn;  
  USN MaxUsn;  
  DWORDLONG MaximumSize;  
  DWORDLONG AllocationDelta;
"""
class USN_JOURNAL_DATA (Data):
  STRUCTURE = parse_structure (USN_JOURNAL_DATA_STRUCT)
    
CREATE_USN_JOURNAL_DATA_STRUCT = u"""
typedef struct {  
  DWORDLONG MaximumSize;  
  DWORDLONG AllocationDelta;
}
"""
class CREATE_USN_JOURNAL_DATA (Data):
  STRUCTURE = parse_structure (CREATE_USN_JOURNAL_DATA_STRUCT)
    

READ_USN_JOURNAL_DATA_STRUCT = u"""
typedef struct {  
  USN StartUsn;  
  DWORD ReasonMask;  
  DWORD ReturnOnlyOnClose;  
  DWORDLONG Timeout;  
  DWORDLONG BytesToWaitFor;  
  DWORDLONG UsnJournalID;
} READ_USN_JOURNAL_DATA
"""
class READ_USN_JOURNAL_DATA (Data):
  STRUCTURE = parse_structure (READ_USN_JOURNAL_DATA_STRUCT)
  
USN_RECORD_STRUCT = u"""
  DWORD RecordLength;  
  WORD MajorVersion;  
  WORD MinorVersion;  
  DWORDLONG FileReferenceNumber;  
  DWORDLONG ParentFileReferenceNumber;  
  USN Usn;  
  LARGE_INTEGER TimeStamp;  
  DWORD Reason;  
  DWORD SourceInfo;  
  DWORD SecurityId;  
  DWORD FileAttributes;  
  WORD FileNameLength;  
  WORD FileNameOffset;  
  WCHAR FileName[1];
"""
class USN_RECORD (Data):
  STRUCTURE = parse_structure (USN_RECORD_STRUCT)


def main ():
  hVolume = CreateFile  (
    ur"\\.\c:", 
    GENERIC_READ, 
    FILE_SHARE_READ | FILE_SHARE_WRITE, 
    None, 
    OPEN_EXISTING, 
    0, 
    None
  )
  #
  # Create journalling if needed
  #
  create_usn_journal_data = CREATE_USN_JOURNAL_DATA (0, 0)
  DeviceIoControl (
    hVolume, 
    winioctlcon.FSCTL_CREATE_USN_JOURNAL, 
    create_usn_journal_data.to_data (), 
    1024,
    None
  )
  
  usn_journal_data = USN_JOURNAL_DATA.from_data (
    DeviceIoControl (
      hVolume,
      winioctlcon.FSCTL_QUERY_USN_JOURNAL,
      None,
      USN_JOURNAL_DATA.size (),
      None
    )
  )
  
  

if __name__ == u'__main__':
  main ()
