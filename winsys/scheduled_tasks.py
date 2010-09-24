# -*- coding: iso-8859-1 -*-
from __future__ import with_statement
import os, sys
import datetime
import operator
import re
import time

import pythoncom
from win32com.taskscheduler import taskscheduler

from constants import *

def _set (obj, key, value):
  obj.__dict__[key] = value

def pytime_to_datetime (pytime):
  return datetime.datetime.fromtimestamp (int (pytime))

def datetime_to_pytime (timestamp):
  return pywintypes.Time (time.mktime (timestamp.timetuple ()))

def flag_to_word (number, prefix):
  for name in (k for k in dir (taskscheduler) if k.startswith (prefix)):
    if getattr (taskscheduler, name) == number:
      return name[len (prefix):].lower ()

def word_to_flag (word, prefix):
  if word is None:
    return None
  elif isinstance (word, int):
    return word
  else:
    return getattr (taskscheduler, prefix + word.upper ())

def flags_to_words (number, prefix):
  words = set ()
  for flag_name in (k for k in dir (taskscheduler) if k.startswith (prefix)):
    flag_value = getattr (taskscheduler, flag_name)
    if flag_value & number:
      words.add (flag_name[len (prefix):].lower ())
  return words

def words_to_flags (flags_as_words, prefix):
  flags = 0
  for word in flags_as_words:
    flags |= getattr (taskscheduler, prefix + word.upper ())
  return flags

def timedelta_to_days (timedelta):
  if timedelta is None:
    return None
  return timedelta.days

def string_to_timedelta (string):
  u"""Match a time interval string of the form <wks>w <days>d <hrs>h <mins>'
  and convert to a timedelta.
  """
  if string is None:
    return None
  else:
    string = str (string).strip ()

  match = re.match (r"(?:(\d+)w)?\W+(?:(\d+)d)?\W*(?:(\d+)h)?\W*(?:(\d+)')?", string)
  if not match:
    raise RuntimeError, u"Interval string must be [<wks>w] [<days>d] [<hours>h] [<mins>']"
  else:
    w, d, h, m = [int (i or 0) for i in match.groups ()]
    print u"string_to_minutes: %dd %dh %d'" % (d, h, m)
    return datetime.timedelta (weeks=w, days=d, hours=h, minutes=m)

def timedelta_to_minutes (timedelta):
  if timedelta is None:
    return None
  return (timedelta.days * 24 * 60) + (timedelta.seconds / 60)

def interval_as_minutes (interval):
  if interval is None:
    return None

  if isinstance (interval, int):
    return interval
  elif isinstance (interval, datetime.timedelta):
    return timedelta_to_minutes (interval)
  else:
    return timedelta_to_minutes (string_to_timedelta (interval))

def interval_as_days (interval):
  if interval is None:
    return None

  if isinstance (interval, int):
    return interval
  elif isinstance (interval, datetime.timedelta):
    return interval.days
  else:
    return string_to_timedelta (interval).days

def interval_as_weeks (interval):
  if interval is None:
    return None

  if isinstance (interval, int):
    return interval
  elif isinstance (interval, datetime.timedelta):
    return interval.days / 7
  else:
    return string_to_timedelta (interval).days / 7

def enum_as_number (enum):
  if enum is None:
    return None

  if isinstance (enum, int):
    return enum
  else:
    return words_to_flags (enum, u"TASK_")

def days_as_bits (days):
  if days is None:
    return None

  if isinstance (days, int):
    return days
  else:
    return reduce (operator.ior, (2**(day-1) for bit in days))

class _ScheduleDetails (object):

  def __init__ (
    self,
    schedule_type,
    start_at,
    end_at=None,
    repeat_every=None,
    repeat_until=None,
    kill_at_end=False,
    is_disabled=False,
    days_interval=None,
    weeks_interval=None,
    days_of_the_week=None,
    month_date=None,
    months=None,
    n_week=None,
    month_days=None
  ):
    self.schedule_type = schedule_type
    self.start_at = start_at
    self.end_at = end_at
    self.repeat_every = interval_as_minutes (repeat_every)
    if isinstance (repeat_until, datetime.datetime):
      repeat_until = repeat_until - self.start_datetime
    self.repeat_until = interval_as_minutes (repeat_until)
    self.kill_at_end  = kill_at_end
    self.is_disabled = is_disabled
    self.days_interval = interval_as_days (days_interval)
    self.weeks_interval = interval_as_weeks (weeks_interval)
    self.days_of_the_week = enum_as_number (days_of_the_week)
    self.month_date = month_date
    self.months = enum_as_number (months)
    self.n_week = word_to_flag (n_week, "TASK_")
    self.month_days = days_as_bits (month_days)

def once_schedule (
  start_at,
  end_at=None,
  repeat_every=None,
  repeat_until=None,
  kill_at_end=False,
  is_disabled=False
):
  return _ScheduleDetails (
    0,
    start_at,
    end_at,
    repeat_every,
    repeat_until,
    kill_at_end,
    is_disabled
  )

def daily_schedule (
  start_at,
  every_n_days,
  end_at=None,
  repeat_every=None,
  repeat_until=None,
  kill_at_end=False,
  is_disabled=False
):
  return _ScheduleDetails (
    1,
    start_at,
    end_at,
    repeat_every,
    repeat_until,
    kill_at_end,
    is_disabled,
    every_n_days
  )

def weekly_schedule (
  start_at,
  every_n_weeks,
  weekdays,
  end_at=None,
  repeat_every=None,
  repeat_until=None,
  kill_at_end=False,
  is_disabled=False
):
  return _ScheduleDetails (
    2,
    start_at,
    end_at,
    repeat_every,
    repeat_until,
    kill_at_end,
    is_disabled,
    every_n_weeks,
    weekdays
  )

class Schedule (object):

  def __init__ (
    self,
    trigger
  ):
    _set (self, u"trigger", trigger)

  def __getattr__ (self, attr):
    return getattr (self.trigger, attr)

  def __setattr__ (self, attr, value):
    setattr (self.trigger, attr, value)

  def __str__ (self):
    return self.trigger.GetTriggerString ()

class Schedules (object):

  def __init__ (self, task):
    self.task = task

  def __len__ (self):
    return self.task.GetTriggerCount ()

  def __getitem__ (self, index):
    return self.get_schedule (index)

  def __iter__ (self):
    for n_trigger in range (self.task.GetTriggerCount ()):
      yield self.get_schedule (n_trigger)

  def get_schedule (self, n_trigger):
    return Schedule (self.task.GetTrigger (n_trigger))

  def add (self, schedule_details):
    n_trigger, trigger = self.task.CreateTrigger ()
    #~ schedule = Schedule (schedule)
    trigger.SetTrigger (schedule_details)
    return self.get_schedule (n_trigger)

class Task (object):

  def __init__ (self, name, task, **kwargs):
    self.name = name
    self.task = task
    self.schedules = Schedules (self)
    for k, v in kwargs.iteritems ():
      setattr (self, k, v)

  def add_schedule (self, schedule):
    return self.schedules.add (schedule)

  def get_application_name (self):
    return self.task.GetApplicationName ()
  def set_application_name (self, application_name):
    self.task.SetApplicationName (application_name)
  application_name = property (get_application_name, set_application_name)

  def get_parameters (self):
    return self.task.GetParameters ()
  def set_parameters (self, parameters):
    self.task.SetParameters (parameters)
  parameters = property (get_parameters, set_parameters)

  def get_working_directory (self):
    return self.task.GetWorkingDirectory ()
  def set_working_directory (self, working_directory):
    self.task.SetWorkingDirectory (working_directory)
  working_directory = property (get_working_directory, set_working_directory)

  def get_priority (self):
    return self.task.GetPriority ()
  def set_priority (self, priority):
    self.task.SetPriority (priority)
  priority = property (get_priority, set_priority)

  def get_task_flags (self):
    return flags_to_words (self.task.GetTaskFlags (), prefix=u"TASK_FLAG_")
  def set_task_flags (self, task_flags):
    try:
      flags = int (task_flags)
    except (ValueError, TypeError):
      flags = self.words_to_flags (task_flags, u"TASK_FLAG_")
    self.task.SetTaskFlags (flags)
  task_flags = property (get_task_flags, set_task_flags)

  def get_max_run_time (self):
    return self.task.GetMaxRunTime ()
  def set_max_run_time (self, max_run_time):
    self.task.SetMaxRunTime (max_run_time)
  max_run_time = property (get_max_run_time, set_max_run_time)

  def get_comment (self):
    return self.task.GetComment ()
  def set_comment (self, comment):
    self.task.SetComment (comment)
  comment = property (get_comment, set_comment)

  def get_creator (self):
    return self.task.GetCreator ()
  def set_creator (self, creator):
    self.task.SetCreator (creator)
  creator = property (get_creator, set_creator)

  def get_account_information (self):
    return self.task.GetAccountInformation ()
  def set_account_information (self, account_name_password):
    self.task.SetAccountInformation (*account_name_password)
  account_information = property (get_account_information, set_account_information)

  def get_work_item_data (self):
    return self.task.GetWorkItemData ()
  def set_work_item_data (self, data):
    self.task.SetWorkItemData (data)
  work_item_data = property (get_work_item_data, set_work_item_data)

  def get_next_run_time (self):
    return pytime_to_datetime (self.task.GetNextRunTime ())
  next_run_time = property (get_next_run_time)

  def get_most_recent_run_time (self):
    return pytime_to_datetime (self.task.GetMostRecentRunTime ())
  most_recent_run_time = property (get_most_recent_run_time)

  def run_times (self, n_to_fetch=1):
    return [pytime_to_datetime (run_time) for run_time in self.task.GetRunTimes (n_to_fetch)]

  def get_idle_wait (self):
    return self.task.GetIdleWait ()
  def set_idle_wait (self, idle_wait_and_deadline_mins):
    self.task.SetIdleWait (*idle_wait_and_deadline_mins)
  idle_wait = property (get_idle_wait, set_idle_wait)

  def get_status (self):
    return flag_to_word (self.task.GetStatus (), u"SCHED_S_")
  status = property (get_status)

  def get_exit_code (self):
    return self.task.GetExitCode ()
  exit_code = property (get_exit_code)

  @staticmethod
  def _int_to_ext (internal_attribute):
    words = internal_attribute.split ("_")
    return u"Get" + "".join (word.title () for word in words)

  def _ext_to_int (external_attribute):
    words = re.findall ("Get((?:[A-Z][a-z]+)+)", external_attribute)
    return "_".join (word.lower () for word in words if word)

  def __str__ (self):
    return "<Task: %s>" % self.name

  def save (self):
    self.task.QueryInterface (pythoncom.IID_IPersistFile).Save (None, 1)

class Tasks (object):

  def __init__ (self, computer=""):
    self.tasks = pythoncom.CoCreateInstance (
      taskscheduler.CLSID_CTaskScheduler,
      None,
      pythoncom.CLSCTX_INPROC_SERVER,
      taskscheduler.IID_ITaskScheduler
    )
    if computer:
      if not computer.startswith (u"\\\\"):
        computer = u"\\\\" + computer
      self.tasks.SetTargetComputer (computer)

  def __iter__ (self):
    for name in self.tasks.Enum ():
      yield Task (name, self.tasks.Activate (name))

  def __getitem__ (self, name):
    return self.get (name)

  def get (self, name):
    return Task (name, self.tasks.Activate (name))

  def add (self, name, **kwargs):
    task = self.tasks.NewWorkItem (name)
    return Task (name, task, **kwargs)

  def remove (self, name):
    self.tasks.Delete (name)

def task (name):
  return tasks ().get (name)

def tasks ():
  return Tasks ()

def add (name, **kwargs):
  return tasks ().add (name, **kwargs)

def remove (name):
  return tasks ().remove (name)

if __name__ == '__main__':
  for task in tasks ():
    print task
    for schedule in task.schedules:
      print "  ", schedule
    print
