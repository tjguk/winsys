@echo off
.venv\scripts\python -mtests
IF ERRORLEVEL 1 goto finish

:finish
PAUSE