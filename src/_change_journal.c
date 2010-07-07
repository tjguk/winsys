#include <python.h>
#include <datetime.h>
#include <structmember.h>

#define UNICODE
#include <tchar.h>
#include <wchar.h>
#include <windows.h>
#include <winioctl.h>

/*
Utility functions
*/

BOOL
query_change_journal (HANDLE hVolume, USN_JOURNAL_DATA *journal_data)
{
BOOL is_ok;
int n_bytes;

  Py_BEGIN_ALLOW_THREADS
  is_ok = DeviceIoControl (
    hVolume,
    FSCTL_QUERY_USN_JOURNAL, // action
    NULL, 0, // in-buffer & size
    journal_data, sizeof (*journal_data), &n_bytes,  // out buffer & size & bytes written
    NULL // Overlap structure
  );
  Py_END_ALLOW_THREADS
  if (!is_ok)
    PyErr_SetFromWindowsErr (GetLastError ());
  return is_ok;
}

BOOL
add_n_to_dict (PyObject *dict, const char *name, DWORDLONG n)
{
PyObject *pylong;

  pylong = PyLong_FromLongLong (n);
  if (!pylong)
    return FALSE;
  if (PyDict_SetItemString (dict, name, pylong) == -1)
    return FALSE;

  Py_DECREF (pylong);
  return TRUE;
}

PyObject *
usn2dict (PUSN_RECORD usn_record)
{
PyObject *dict;
PyObject *pytimestamp;
PyObject *pyfilename;
FILETIME filetime;
SYSTEMTIME systemtime, localtime;

  dict = PyDict_New ();
  if (dict == NULL)
    return NULL;

  if (!add_n_to_dict (dict, "RecordLength", usn_record->RecordLength)) goto failure;
  if (!add_n_to_dict (dict, "MajorVersion", usn_record->MajorVersion)) goto failure;
  if (!add_n_to_dict (dict, "MinorVersion", usn_record->MinorVersion)) goto failure;
  if (!add_n_to_dict (dict, "FileReferenceNumber", usn_record->FileReferenceNumber)) goto failure;
  if (!add_n_to_dict (dict, "ParentFileReferenceNumber", usn_record->ParentFileReferenceNumber)) goto failure;
  if (!add_n_to_dict (dict, "Usn", usn_record->Usn)) goto failure;
  if (!add_n_to_dict (dict, "Reason", usn_record->Reason)) goto failure;
  if (!add_n_to_dict (dict, "SourceInfo", usn_record->SourceInfo)) goto failure;
  if (!add_n_to_dict (dict, "SecurityId", usn_record->SecurityId)) goto failure;
  if (!add_n_to_dict (dict, "FileAttributes", usn_record->FileAttributes)) goto failure;

  filetime.dwLowDateTime = usn_record->TimeStamp.LowPart;
  filetime.dwHighDateTime = usn_record->TimeStamp.HighPart;
  FileTimeToSystemTime (&filetime, &systemtime);
  SystemTimeToTzSpecificLocalTime (NULL, &systemtime, &localtime);
  pytimestamp = PyDateTime_FromDateAndTime (
    localtime.wYear, localtime.wMonth, localtime.wDay,
    localtime.wHour, localtime.wMinute, localtime.wSecond,
    1000 * localtime.wMilliseconds
  );
  if (!pytimestamp)
    goto failure;
  if (PyDict_SetItemString (dict, "TimeStamp", pytimestamp) == -1)
    goto failure;

  pyfilename = PyUnicode_FromWideChar (
    ((PBYTE)usn_record) + usn_record->FileNameOffset,
    usn_record->FileNameLength / sizeof (WCHAR)
  );
  if (!pyfilename)
    goto failure;
  if (PyDict_SetItemString (dict, "FileName", pyfilename) == -1)
    goto failure;

  Py_DECREF (pytimestamp);
  Py_DECREF (pyfilename);
  return dict;

failure:
  Py_XDECREF (pytimestamp);
  Py_XDECREF (pyfilename);
  Py_DECREF (dict);
  return NULL;
}

typedef struct {
    PyObject_HEAD

    HANDLE handle;
    PyObject *volume_name;
} ChangeJournal;

/*
ChangeJournal journal iterator structures
*/
#define buffer_length 20480
typedef struct {
  PyObject_HEAD
  HANDLE handle;
  READ_USN_JOURNAL_DATA read_journal_data;
  BOOL buffer_needs_refresh;
  char buffer[buffer_length];
  int n_bytes_read;
  int n_bytes_left;
  PUSN_RECORD usn_record;
} JournalIterator;

static PyObject *
jit_new (PyTypeObject *type, PyObject *args, PyObject *kwds)
{
JournalIterator *iterator;

  iterator = (JournalIterator *)type->tp_alloc (type, 0);
  if (iterator != NULL)
  {
    iterator->handle = 0;
    iterator->buffer_needs_refresh = 0;
    memset (iterator->buffer, 0, buffer_length);
    iterator->n_bytes_read = 0;
    iterator->n_bytes_left = 0;
    iterator->buffer_needs_refresh = 1;
    iterator->usn_record = NULL;
  }

  return (PyObject *)iterator;
}

static PyObject *
jit_iternext (PyObject *self)
{
USN next_usn;
PyObject *usn_dict;
JournalIterator *iterator;
BOOL is_ok;

  iterator = (JournalIterator *)self;
  /*
  Refresh the buffer if needed (either because it's
  the first run or because we've exhausted the previous
  buffer contents.
  */

  if (iterator->buffer_needs_refresh)
  {
    iterator->buffer_needs_refresh = 0;
    Py_BEGIN_ALLOW_THREADS
    memset (iterator->buffer, 0, buffer_length);
    is_ok = DeviceIoControl (
      iterator->handle,
      FSCTL_READ_USN_JOURNAL, // action
      &iterator->read_journal_data, sizeof (iterator->read_journal_data), // in-buffer & size
      &iterator->buffer, buffer_length, &iterator->n_bytes_read,  // out buffer & size & bytes written
      NULL // Overlap structure
    );
    Py_END_ALLOW_THREADS

    if (!is_ok) {
      PyErr_SetFromWindowsErr (GetLastError ());
      return NULL;
    };

    next_usn = *(USN *)&iterator->buffer;
    if (next_usn == iterator->read_journal_data.StartUsn)
    {
      PyErr_SetNone(PyExc_StopIteration);
      return NULL;
    }
    else
    {
      iterator->usn_record = (PUSN_RECORD)(((PUCHAR)iterator->buffer) + sizeof (USN));
      iterator->n_bytes_left = iterator->n_bytes_read - sizeof (USN);
      iterator->read_journal_data.StartUsn = next_usn;
    }
  }

  usn_dict = usn2dict (iterator->usn_record);
  if (!usn_dict)
    return NULL;
  iterator->n_bytes_left -= iterator->usn_record->RecordLength;
  iterator->usn_record = (PUSN_RECORD)(((PCHAR)iterator->usn_record) + iterator->usn_record->RecordLength);

  if (iterator->n_bytes_left <= 0)
    iterator->buffer_needs_refresh = 1;

  return usn_dict;
}

PyTypeObject JournalIterator_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "JournalIterator",            /* tp_name */
  sizeof(JournalIterator),      /* tp_basicsize */
  0,                            /* tp_itemsize */
  0,                            /* tp_dealloc */
  0,                            /* tp_print */
  0,                            /* tp_getattr */
  0,                            /* tp_setattr */
  0,                            /* tp_compare */
  0,                            /* tp_repr */
  0,                            /* tp_as_number */
  0,                            /* tp_as_sequence */
  0,                            /* tp_as_mapping */
  0,                            /* tp_hash */
  0,                            /* tp_call */
  0,                            /* tp_str */
  0,                            /* tp_getattro */
  0,                            /* tp_setattro */
  0,                            /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,           /* tp_flags */
  0,                            /* tp_doc */
  0,                            /* tp_traverse */
  0,                            /* tp_clear */
  0,                            /* tp_richcompare */
  0,                            /* tp_weaklistoffset */
  PyObject_SelfIter,            /* tp_iter */
  (iternextfunc)jit_iternext,   /* tp_iternext */
  0,                            /* tp_methods */
  0,                            /* tp_members */
  0,                            /* tp_getset */
  0,                            /* tp_base */
  0,                            /* tp_dict */
  0,                            /* tp_descr_get */
  0,                            /* tp_descr_set */
  0,                            /* tp_dictoffset */
  0,                            /* tp_init */
  0,                            /* tp_alloc */
  jit_new,                      /* tp_new */
};

static PyObject*
journal_iterator (
  ChangeJournal *change_journal,
  USN StartUsn,
  DWORD ReasonMask,
  DWORD ReturnOnlyOnClose,
  DWORDLONG Timeout,
  DWORDLONG BytesToWaitFor
)
{
JournalIterator *iterator;
USN_JOURNAL_DATA journal_data;

  iterator = PyObject_New (JournalIterator, &JournalIterator_Type);
  if (iterator == NULL) {
    return NULL;
  }

  if (change_journal->handle == NULL) {
    PyErr_SetString (PyExc_RuntimeError, "No handle supplied");
    return NULL;
  }
  iterator->handle = change_journal->handle;

  if (!query_change_journal (iterator->handle, &journal_data))
    return NULL;
  iterator->read_journal_data.UsnJournalID = journal_data.UsnJournalID;
  iterator->read_journal_data.StartUsn = StartUsn;
  iterator->read_journal_data.ReasonMask = ReasonMask;
  iterator->read_journal_data.ReturnOnlyOnClose = ReturnOnlyOnClose;
  iterator->read_journal_data.Timeout = Timeout;
  iterator->read_journal_data.BytesToWaitFor = BytesToWaitFor;

  Py_INCREF (iterator);
  return (PyObject *)iterator;
}

static char ChangeJournal_doc[] =
    "Represent the change journal for one volume. Iterating over it will return\n"
    "one set of data for each of the records. For more refined queries, call the\n"
    "read method.";

static PyObject *
ChangeJournal_new (PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  ChangeJournal *self;

  self = (ChangeJournal *)type->tp_alloc (type, 0);
  if (self != NULL)
  {
    self->handle = NULL;
    self->volume_name = PyUnicode_FromString ("<Uninitialised>");
    if (!self->volume_name)
      return NULL;
  }

  return (PyObject *)self;
}

static void
ChangeJournal_dealloc (ChangeJournal *self)
{
  if (self->handle != NULL)
    CloseHandle (self->handle);
  Py_XDECREF (self->volume_name);
  Py_TYPE (self)->tp_free ((PyObject *)self);
}

static int
ChangeJournal_init (ChangeJournal *self, PyObject *args, PyObject *kwds)
{
PyUnicodeObject *device_moniker;
HANDLE hDrive;

  if (!PyArg_ParseTuple (args, "U", &device_moniker))
    return -1;

  Py_BEGIN_ALLOW_THREADS
  hDrive = CreateFile (
    PyUnicode_AS_UNICODE (device_moniker),
    GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL
  );
  Py_END_ALLOW_THREADS

  if (hDrive  == INVALID_HANDLE_VALUE)
  {
    PyErr_SetFromWindowsErr (GetLastError ());
    return -1;
  }

  self->handle = hDrive;
  self->volume_name = (PyObject *)device_moniker;
  Py_INCREF (device_moniker);

  return 0;
}

static PyObject*
ChangeJournal_iter (ChangeJournal *self)
{
  return journal_iterator (
    self,   // change_journal
    0,      // StartUSN
    -1,     // ReasonMask
    FALSE,  // ReturnOnlyOnClose
    0,      // Timeout
    0       // BytesToWaitFor
  );
}

static char ChangeJournal_query_doc[] =
    "query () -> dictionary containing the fields from the USN_JOURNAL_DATA structure:\n"
    "  UsnJournalID - id for this journal; if this changes, the journal has been restarted\n"
    "  FirstUsn - first USN in this journal\n"
    "  NextUsn - the next USN which will be used\n"
    "  LowestValidUsn - will generally be zero\n"
    "  MaxUsn - the maximum USN which will ever be used in this journal; in theory admins ought to"
    "monitor NextUsn to see if it is approaching MaxUsn\n"
    "  MaximumSize - the number of bytes which this journal should grow to\n"
    "  The number of bytes past the MaximumSize which this journal should allow"
    ;
static PyObject *
ChangeJournal_query (ChangeJournal *self)
{
USN_JOURNAL_DATA journal_data;
PyObject *info;

  if (self->handle == NULL) {
    PyErr_SetString (PyExc_RuntimeError, "No handle supplied");
    return NULL;
  }

  if (!query_change_journal (self->handle, &journal_data))
    return NULL;

  info = PyDict_New ();
  PyDict_SetItemString (info, "UsnJournalID", PyLong_FromLongLong (journal_data.UsnJournalID));
  PyDict_SetItemString (info, "FirstUsn", PyLong_FromLongLong (journal_data.FirstUsn));
  PyDict_SetItemString (info, "NextUsn", PyLong_FromLongLong (journal_data.NextUsn));
  PyDict_SetItemString (info, "LowestValidUsn", PyLong_FromLongLong(journal_data.LowestValidUsn));
  PyDict_SetItemString (info, "MaxUsn", PyLong_FromLongLong(journal_data.MaxUsn));
  PyDict_SetItemString (info, "MaximumSize", PyLong_FromLongLong(journal_data.MaximumSize));
  PyDict_SetItemString (info, "AllocationDelta", PyLong_FromLongLong(journal_data.AllocationDelta));
  return info;
}

static PyObject *
ChangeJournal_create (ChangeJournal *self, PyObject *args)
{
DWORDLONG MaximumSize = 0;
DWORDLONG AllocationDelta = 0;

CREATE_USN_JOURNAL_DATA create_journal_data;
DWORD n_bytes;
BOOL is_ok;

  if (self->handle == NULL) {
    PyErr_SetString (PyExc_RuntimeError, "No handle supplied");
    return NULL;
  }

  if (!PyArg_ParseTuple (args, "|ii", &MaximumSize, &AllocationDelta))
    return NULL;

  create_journal_data.MaximumSize = MaximumSize;
  create_journal_data.AllocationDelta = AllocationDelta;
  Py_BEGIN_ALLOW_THREADS
  is_ok = DeviceIoControl (
    self->handle,
    FSCTL_CREATE_USN_JOURNAL, // action
    &create_journal_data, sizeof (create_journal_data), // in-buffer & size
    NULL, 0, &n_bytes,  // out buffer & size & bytes written
    NULL // Overlap structure
  );
  Py_END_ALLOW_THREADS
  if (!is_ok) {
    return PyErr_SetFromWindowsErr (GetLastError ());
  }

  Py_RETURN_NONE;
}

static PyObject *
ChangeJournal_delete (ChangeJournal *self, PyObject *args)
{
int DeleteNow = 1;
int Notify = 0;

USN_JOURNAL_DATA journal_data;
DELETE_USN_JOURNAL_DATA delete_journal_data;
DWORD n_bytes;
BOOL is_ok;

  if (self->handle == NULL) {
    PyErr_SetString (PyExc_RuntimeError, "No handle supplied");
    return NULL;
  }

  if (!PyArg_ParseTuple (args, "|ii", &DeleteNow, &Notify))
    return NULL;

  if (!query_change_journal (self->handle, &journal_data))
    return NULL;

  delete_journal_data.UsnJournalID = journal_data.UsnJournalID;
  delete_journal_data.DeleteFlags = 0;
  if (DeleteNow) delete_journal_data.DeleteFlags |= USN_DELETE_FLAG_DELETE;
  if (Notify) delete_journal_data.DeleteFlags |= USN_DELETE_FLAG_NOTIFY;
  Py_BEGIN_ALLOW_THREADS
  is_ok = DeviceIoControl (
    self->handle,
    FSCTL_DELETE_USN_JOURNAL, // action
    &delete_journal_data, sizeof (delete_journal_data), // in-buffer & size
    NULL, 0, &n_bytes,  // out buffer & size & bytes written
    NULL // Overlap structure
  );
  Py_END_ALLOW_THREADS
  if (!is_ok) {
    return PyErr_SetFromWindowsErr (GetLastError ());
  }

  Py_RETURN_NONE;
};

static PyObject *
ChangeJournal_read (ChangeJournal *self, PyObject *args, PyObject *kwargs)
{
USN StartUsn = 0;
DWORD ReasonMask = -1;
DWORD ReturnOnlyOnClose = FALSE;
DWORDLONG Timeout = 0;
DWORDLONG BytesToWaitFor = 0;
static char *kwlist[] = {"start_usn", "reason_mask", "return_only_on_close", "timeout", "bytes_to_wait_for", NULL};

  if (self->handle == NULL) {
    PyErr_SetString (PyExc_RuntimeError, "No handle supplied");
    return NULL;
  }

  if (!PyArg_ParseTupleAndKeywords (args, kwargs, "|iiiii", kwlist,
                                    &StartUsn, &ReasonMask, &ReturnOnlyOnClose, &Timeout, &BytesToWaitFor))
    return NULL;

  return journal_iterator (
    self,
    StartUsn,
    ReasonMask,
    ReturnOnlyOnClose,
    Timeout,
    BytesToWaitFor
  );
}

static PyMemberDef ChangeJournal_members[] = {
  {"volume_name", T_OBJECT_EX, offsetof (ChangeJournal, volume_name), 0, "Volume name"},
  {NULL}
};

static PyMethodDef ChangeJournal_methods[] = {
  {"query", (PyCFunction)ChangeJournal_query, METH_NOARGS, ChangeJournal_query_doc},
  {"create", (PyCFunction)ChangeJournal_create, METH_VARARGS, "Create the changelog"},
  {"delete", (PyCFunction)ChangeJournal_delete, METH_VARARGS, "Delete the changelog"},
  {"read", (PyCFunction)ChangeJournal_read, METH_VARARGS | METH_KEYWORDS, "Read the changelog"},
  {NULL}
};

static PyTypeObject ChangeJournalType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_change_journal.ChangeJournal",  /* tp_name */
    sizeof(ChangeJournal), /* tp_basicsize */
    0,                     /* tp_itemsize */
    ChangeJournal_dealloc, /* tp_dealloc */
    0,                     /* tp_print */
    0,                     /* tp_getattr */
    0,                     /* tp_setattr */
    0,                     /* tp_reserved */
    0,                     /* tp_repr */
    0,                     /* tp_as_number */
    0,                     /* tp_as_sequence */
    0,                     /* tp_as_mapping */
    0,                     /* tp_hash  */
    0,                     /* tp_call */
    0,                     /* tp_str */
    0,                     /* tp_getattro */
    0,                     /* tp_setattro */
    0,                     /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,    /* tp_flags */
    ChangeJournal_doc,     /* tp_doc */
    0,                     /* tp_traverse */
    0,                     /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    ChangeJournal_iter,    /* tp_iter */
    0,                     /* tp_iternext */
    ChangeJournal_methods, /* tp_methods */
    ChangeJournal_members, /* tp_members */
    0,                     /* tp_getset */
    0,                     /* tp_base */
    0,                     /* tp_dict */
    0,                     /* tp_descr_get */
    0,                     /* tp_descr_set */
    0,                     /* tp_dictoffset */
    ChangeJournal_init,    /* tp_init */
    0,                     /* tp_alloc */
    PyType_GenericNew      /* tp_new */
};

PyObject *
_change_journal_file_info (PyObject *self, PyObject *args)
{
PyUnicodeObject *filename;
PUSN_RECORD usn_record;
DWORD n_bytes;
HANDLE hFile;
BOOL is_ok;
PyObject *dict;

  if (!PyArg_ParseTuple (args, "U", &filename))
    return NULL;

  Py_BEGIN_ALLOW_THREADS
  hFile = CreateFile (
    PyUnicode_AS_UNICODE (filename),
    GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL
  );
  Py_END_ALLOW_THREADS

  if (hFile == INVALID_HANDLE_VALUE)
  {
    PyErr_SetFromWindowsErr (GetLastError ());
    goto failure;
  }

  usn_record = (PUSN_RECORD)malloc (sizeof (USN_RECORD) + MAX_PATH);
  if (usn_record == NULL)
    return PyErr_NoMemory();

  Py_BEGIN_ALLOW_THREADS
  is_ok = DeviceIoControl (
    hFile,
    FSCTL_READ_FILE_USN_DATA, // action
    NULL, 0, // in-buffer & size
    usn_record, sizeof (USN_RECORD) + MAX_PATH, &n_bytes,  // out buffer & size & bytes written
    NULL // Overlap structure
  );
  Py_END_ALLOW_THREADS
  if (!is_ok) {
    PyErr_SetFromWindowsErr (GetLastError ());
    goto failure;
  }

  dict = usn2dict (usn_record);
  if (!dict)
    goto failure;

  Py_BEGIN_ALLOW_THREADS
  is_ok = CloseHandle (hFile);
  Py_END_ALLOW_THREADS
  if (!is_ok) {
    PyErr_SetFromWindowsErr (GetLastError ());
    goto failure;
  }

  return dict;

failure:
  if (hFile != INVALID_HANDLE_VALUE)
    CloseHandle (hFile);
  Py_XDECREF (dict);
  return NULL;
}

void
add_constants (PyObject *module)
{
  PyModule_AddIntMacro (module, USN_REASON_DATA_OVERWRITE);
  PyModule_AddIntMacro (module, USN_REASON_DATA_EXTEND);
  PyModule_AddIntMacro (module, USN_REASON_DATA_TRUNCATION);
  PyModule_AddIntMacro (module, USN_REASON_NAMED_DATA_OVERWRITE);
  PyModule_AddIntMacro (module, USN_REASON_NAMED_DATA_EXTEND);
  PyModule_AddIntMacro (module, USN_REASON_NAMED_DATA_TRUNCATION);
  PyModule_AddIntMacro (module, USN_REASON_FILE_CREATE);
  PyModule_AddIntMacro (module, USN_REASON_FILE_DELETE);
  PyModule_AddIntMacro (module, USN_REASON_EA_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_SECURITY_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_RENAME_OLD_NAME);
  PyModule_AddIntMacro (module, USN_REASON_RENAME_NEW_NAME);
  PyModule_AddIntMacro (module, USN_REASON_INDEXABLE_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_BASIC_INFO_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_HARD_LINK_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_COMPRESSION_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_ENCRYPTION_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_OBJECT_ID_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_REPARSE_POINT_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_STREAM_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_TRANSACTED_CHANGE);
  PyModule_AddIntMacro (module, USN_REASON_CLOSE);
};


static PyMethodDef usn_methods[] = {
  {"file_info",  _change_journal_file_info, METH_VARARGS, "Get USN info for a file"},
  {NULL, NULL, 0, NULL}
};
static struct PyModuleDef usn_module = {
  PyModuleDef_HEAD_INIT,
  "_change_journal",
  "Docstring for ChangeJournal",
  -1,
  usn_methods
};

PyMODINIT_FUNC
PyInit__change_journal (void)
{
PyObject *_change_journal_module;

  PyDateTime_IMPORT;

  _change_journal_module = PyModule_Create(&usn_module);
  if (_change_journal_module ==  NULL)
      return NULL;
  add_constants (_change_journal_module);

  if (PyType_Ready(&ChangeJournalType) < 0)
      return NULL;
  Py_INCREF (&ChangeJournalType);
  PyModule_AddObject (_change_journal_module, "ChangeJournal", (PyObject *)&ChangeJournalType);

  return _change_journal_module;
}
