@echo off
setlocal
cd /d "%~dp0..\backend"
if not exist "..\.venv\Scripts\python.exe" (
  echo Root .venv is missing. See README setup instructions.
  exit /b 1
)
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
exit /b %errorlevel%
