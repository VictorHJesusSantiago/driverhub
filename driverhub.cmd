@echo off
REM DriverHub launcher para Windows
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.9+ e tente novamente.
  exit /b 1
)
python -m driverhub %*
endlocal