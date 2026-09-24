@echo off
cd /d "%~dp0"
python -X utf8 backend\local_workbench.py --open
if errorlevel 1 pause
