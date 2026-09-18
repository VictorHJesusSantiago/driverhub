@echo off
REM DriverHub launcher para Windows
REM Uso: driverhub [--elevate] <comandos...>
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$e = $args | Where-Object { $_ -eq '--elevate' }; " ^
  "$a = $args | Where-Object { $_ -ne '--elevate' }; " ^
  "if ($e) { Start-Process -Verb RunAs -Wait python -ArgumentList @('-m','driverhub') + $a; exit $LASTEXITCODE } " ^
  "else { python -m driverhub @a; exit $LASTEXITCODE }" %*