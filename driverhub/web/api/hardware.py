# -*- coding: utf-8 -*-
"""Rotas de hardware: árvore agregada, sensores e discos."""
from __future__ import annotations


def get_hardware(store):
    """Agrega sensores/discos/ram/cpu + rede e GPU numa árvore única."""
    try:
        from ...core import platform
        info = platform.detect_all()
        tree = {
            "os": info.get("os", {}),
            "device_class": info.get("device_class", ""),
            "cpu": info.get("cpu", {}),
            "ram": info.get("ram", {}),
            "disks": info.get("disks", []),
            "gpu": info.get("gpu", []),
            "network": info.get("network", []),
            "sensors": info.get("sensors", {}),
            "timestamp": info.get("timestamp", ""),
        }
        return {"hardware": tree}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao agregar hardware: {exc}"}


def get_sensors():
    """Lê sensores (temperaturas, ventoinhas, bateria) do sistema."""
    try:
        from ...core import platform
        sensors = platform.detect_sensors() or {}
        items = []
        for group, data in sensors.items():
            if isinstance(data, dict):
                for name, value in data.items():
                    items.append({"group": group, "name": name, "value": value})
            else:
                items.append({"group": group, "name": group, "value": data})
        return {"sensors": sensors, "items": items, "total": len(items)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao ler sensores: {exc}"}


def get_disks():
    """Lista as partições/discos montados com uso de espaço."""
    try:
        from ...core import platform
        disks = platform.detect_disks() or []
        return {"items": disks, "total": len(disks)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao ler discos: {exc}"}