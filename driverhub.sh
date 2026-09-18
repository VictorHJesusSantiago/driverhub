#!/usr/bin/env sh
# DriverHub launcher para Linux/macOS/Termux
# Uso: driverhub [--elevate] <comandos...>
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python nao encontrado. Instale Python 3.9+ e tente novamente."
    exit 1
fi

if [ "$1" = "--elevate" ]; then
    shift
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec "$PY" -m driverhub "$@"
    else
        exec sudo "$PY" -m driverhub "$@"
    fi
fi
exec "$PY" -m driverhub "$@"