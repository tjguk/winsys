@echo off
.venv\scripts\python -m winsys.tests
IF ERRORLEVEL 1 goto finish

:finish
