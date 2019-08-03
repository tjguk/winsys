@echo off
cls
.venv\scripts\python -munittest
IF ERRORLEVEL 1 goto finish

:finish
PAUSE