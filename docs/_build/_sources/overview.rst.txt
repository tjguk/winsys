An Overview of WinSys
=====================

Raison d'Être
-------------
Python plus the pywin32 extensions together make an excellent toolkit for
many Windows sysadmin tasks, whether lightweight and *ad hoc* or regular and substantial.
One of the obstacles, though, is that the Python core library is at best
neutered by cross-platform constraints, and at worst simply unfriendly
towards Windows. Another is that the pywin32 extensions, representing
goodness-knows how many man years of development work, are underdocumented
and sometimes quite daunting. You need two levels understanding to make
best use of them: a knowledge of the underlying API which they're wrapping,
and a knowledge of how much the wrapping mechanism has done for you and
how much you have to do for yourself.

For years, in support of our Windows sysadmins, and to help posters on
the python and python-win32 mailing lists, I've been putting together
examples, modules, lightweight wrappers and explanations to achieve
concrete tasks using Python on a Windows platform. It's frustrating,
especially to someone who's used to the high-level nature of Python,
to have to post up 17 lines of code to achieve programatically a
one-line concept. Equally frustrating is the experience of doing a
GetFirst-While-GetNext dance instead of the familiar Python iteration.

Enter WinSys: the Python toolkit for Windows administration tasks.
There's nothing here you couldn't do for yourself in a few minutes
with the pywin32 docs and an internet connection to MSDN. But it's
all a bit more Pythonic. And it's got a fairly consistent approach.
And the constants are a bit more friendly. And you can fairly well
mix and match with raw pywin32 or even ctypes if you need to.

What's On Offer?
----------------
The intention is to expand the areas on offer pretty much on-demand.
Two key modules which aren't included here yet but which continue
to be maintained externally are my own WMI and active_directory modules.
Both are long overdue for an overhaul. The latter has a number of
(more competent) rivals while the former stands more or less alone
but is in need of a bit of a shakedown.

