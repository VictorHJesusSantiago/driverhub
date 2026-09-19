# -*- coding: utf-8 -*-
"""Interação com ``udevadm`` e regras udev.

Propriedades de dispositivos, recarregamento de regras, trigger de eventos e
monitoramento não-bloqueante. As funções nunca lançam exceção.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List


def _udevadm() -> str:
    return shutil.which("udevadm") or ""


def _run(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    exe = _udevadm()
    if not exe:
        return {"ok": False, "output": "", "code": -1,
                "error": "udevadm não encontrado."}
    try:
        proc = subprocess.run([exe] + args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        out = (proc.stdout or "").strip()
        return {"ok": proc.returncode == 0, "output": out,
                "code": proc.returncode, "error": out if proc.returncode else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "code": -2, "error": "tempo esgotado"}
    except Exception as exc:
        return {"ok": False, "output": "", "code": -3, "error": str(exc)}


def property(device: str, timeout: int = 30) -> Dict[str, Any]:
    """Retorna as propriedades udev de um dispositivo ('' se ausente).

    ``device`` pode ser um caminho (``/sys/...`` ou ``/dev/...``) ou nome.
    Use prefixo ``path=`` para forçar ``--path``.
    """
    if not device:
        return {"ok": False, "device": "", "properties": {}, "detail": "Dispositivo vazio."}
    if device.startswith("path="):
        flag, value = "--path", device[len("path="):]
    elif device.startswith("/dev") or device.startswith("/sys"):
        flag = "--path" if device.startswith("/sys") else "--name"
        value = device
    else:
        flag, value = "--name", device
    result = _run(["info", "--query=property", flag, value], timeout=timeout)
    props: Dict[str, str] = {}
    for line in result["output"].splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            props[key.strip()] = val.strip()
    return {"ok": result["ok"], "device": device, "properties": props,
            "count": len(props),
            "detail": result["error"] or f"{len(props)} propriedades."}


def reload_rules() -> Dict[str, Any]:
    """Recarrega as regras udev (``udevadm control --reload-rules``)."""
    result = _run(["control", "--reload-rules"], timeout=30)
    return {"ok": result["ok"],
            "detail": result["error"] or "Regras udev recarregadas.",
            "output": result["output"]}


def trigger(param: str = "") -> Dict[str, Any]:
    """Dispara eventos udev para o dispositivo/subssistema ``param``.

    Ex.: ``trigger("subsystem-match=usb")``. Chamada sem param dispara tudo
    (lenta). Nunca lança.
    """
    args = ["trigger"]
    if param:
        args.extend(param.split())
    result = _run(args, timeout=120)
    return {"ok": result["ok"],
            "detail": result["error"] or "Trigger udev executado.",
            "output": result["output"]}


def monitor(timeout: int = 5, subsystem: str = "") -> Dict[str, Any]:
    """Monitora eventos udev por ``timeout`` segundos (não-bloqueante).

    Retorna os eventos capturados como lista. Como é uma janela curta, os
    eventos podem vir vazios — isso é esperado e não é erro.
    """
    exe = _udevadm()
    if not exe:
        return {"ok": False, "events": [], "detail": "udevadm não encontrado."}
    events: List[str] = []
    capture: List[str] = []
    stop = threading.Event()

    def _reader(proc: Any) -> None:
        if proc.stdout:
            for line in proc.stdout:
                if stop.is_set():
                    break
                capture.append(line.rstrip())

    args = ["monitor"]
    if subsystem:
        args.extend(["--subsystem-match", subsystem])
    try:
        proc = subprocess.Popen([exe] + args, text=True, errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        thread = threading.Thread(target=_reader, args=(proc,), daemon=True)
        thread.start()
        time.sleep(timeout)
        stop.set()
        proc.terminate()
        thread.join(timeout=2)
    except Exception as exc:
        return {"ok": False, "events": [], "detail": str(exc)}
    events = [e for e in capture if e.strip()]
    return {"ok": True, "events": events, "count": len(events),
            "detail": f"{len(events)} evento(s) em {timeout}s.",
            "monitored_for": timeout}


def add_rule(rule: str) -> Dict[str, Any]:
    """Adiciona uma regra udev (não confiável p/ regras maliciosas).

    Grava apenas em ``/run/udev/rules.d`` (dir efêmero) como
    ``60-driverhub.rules`` — jamais toca em regras do sistema.
    """
    import os  # lazy
    import tempfile  # lazy

    rules_dir = "/run/udev/rules.d"
    if not os.path.isdir(rules_dir):
        return {"ok": False, "detail": f"{rules_dir} não existe (sem systemd?)."}
    path = os.path.join(rules_dir, "60-driverhub.rules")
    try:
        with tempfile.NamedTemporaryFile("w", dir=rules_dir, suffix=".tmp",
                                         delete=False, encoding="utf-8") as fh:
            fh.write(rule.strip() + "\n")
            tmp = fh.name
        os.replace(tmp, path)
        os.chmod(path, 0o644)
    except Exception as exc:
        return {"ok": False, "detail": f"Falha ao gravar regra: {exc}"}
    reload = reload_rules()
    return {"ok": True, "path": path, "rule": rule.strip(),
            "detail": "Regra gravada; recarga:"
                      f"{'ok' if reload['ok'] else reload.get('detail', '')}"}