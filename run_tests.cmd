@echo off
.venv\scripts\python -munittest discover
IF ERRORLEVEL 1 goto finish

:finish
PAUSE