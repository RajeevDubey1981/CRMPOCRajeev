@echo off
setlocal
cd /d "%~dp0"
echo Running deployment preflight checks...
py scripts\deploy_preflight.py
if errorlevel 1 (
  echo.
  echo Deployment preflight failed. No deployment was started.
  pause
  exit /b 1
)
echo.
py scripts\deploy.py
if errorlevel 1 (
  echo.
  echo Deploy failed.
  pause
  exit /b 1
)
echo.
pause
