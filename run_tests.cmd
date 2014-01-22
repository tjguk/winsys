@echo off
py -2.6 -m winsys.tests.__main__
IF ERRORLEVEL 1 goto finish
py -2.7 -m winsys.tests
IF ERRORLEVEL 1 goto finish
py -3.2 -m winsys.tests
IF ERRORLEVEL 1 goto finish
py -3.3 -m winsys.tests
IF ERRORLEVEL 1 goto finish

:finish
