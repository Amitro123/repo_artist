@echo off
REM Repo-Artist CLI Wrapper for Windows
REM Sets PYTHONPATH and runs the CLI

set PYTHONPATH=%~dp0
python "%~dp0scripts\cli.py" %*
