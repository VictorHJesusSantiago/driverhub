# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes das sondas de baixo nível (driverhub/core/probes).

Foco em parsers puros (lspci -mm, /proc/sysfs fake paths, modinfo,
udevadm export-db, kextstat) e nas tabelas de IDs PCI/USB. Nada executa
binários do sistema: paths são simulados via mock e plataforma-gatings são
contornados testando as funções puras internas.
"""

import os
import unittest
from unittest import mock

from driverhub.core.probes import kextstat as kextstat_probe
from driverhub.core.probes import lspci as lspci_probe
from driverhub.core.probes import modinfo as modinfo_probe
from driverhub.core.probes import pci as pci_probe
from driverhub.core.probes import sysfs as sysfs_probe
from driverhub.core.probes import udevadm as udevadm_probe
from driverhub.core.probes import usb as usb_probe


class PciLspciTest(unittest.TestCase):
    """pci_parse_mm: parser 'lspci -mmnn' (probes/lspci.py)."""

    def test_parse_mm(self):
        text = (
            '00:02.0 "VGA compatible controller" "Intel Corporation" "HD Graphics 620" [8086:5917]\n'
            '01:00.0 "Ethernet controller" "Realtek Semiconductor Co., Ltd." "RTL8111/8168" [10ec:8168]\n'
        )
        devices = lspci_probe._parse_mm(text)
        self.assertEqual(len(devices), 2)
        first = devices[0]
        self.assertEqual(first["slot"], "00:02.0")
        self.assertEqual(first["class_name"], "Display")
        self.assertEqual(first["vid"], "8086")
        self.assertEqual(first["pid"], "5917")
        second = devices[1]
        self.assertEqual(second["class_name"], "Rede")
        self.assertEqual(second["pci_id"], "10EC:8168")

    def test_pci_class_name_lookup(self):
        self.assertEqual(lspci_probe.pci_class_name("03"), "Display/VGA")
        self.assertEqual(lspci_probe.pci_class_name("06"), "Bridge")


class SysfsTest(unittest.TestCase):
    """Sondas /sys e /proc com paths simulados via mock (sem sistema real)."""

    def test_proc_cpuinfo_with_fake_read(self):
        text = (
            "processor\t: 0\n"
            "model name\t: Intel(R) Core(TM) i5-8250U\n"
            "\n"
            "processor\t: 1\n"
            "model name\t: Intel(R) Core(TM) i5-8250U\n"
        )
        with mock.patch("driverhub.core.probes.sysfs._read", return_value=text):
            cpus = sysfs_probe.proc_cpuinfo()
        self.assertEqual(len(cpus), 2)
        self.assertEqual(cpus[0]["model name"], "Intel(R) Core(TM) i5-8250U")
        self.assertEqual(cpus[0]["processor"], "0")

    def test_proc_modules_with_fake_read(self):
        text = (
            "ext4 585728 3 cryptd,usb_storage Live 0x0000000000000000\n"
            "ntfs3 139264 0 - Live 0x0000000000000001\n"
        )
        with mock.patch("driverhub.core.probes.sysfs._read", return_value=text):
            mods = sysfs_probe.proc_modules()
        self.assertEqual(len(mods), 2)
        first = mods[0]
        self.assertEqual(first["name"], "ext4")
        self.assertEqual(first["size"], "585728")
        self.assertEqual(first["used_by"], "cryptd,usb_storage")
        self.assertEqual(first["state"], "Live")

    def test_sysfs_class_fake_listdir(self):
        with mock.patch(
            "driverhub.core.probes.sysfs.os.listdir",
            return_value=["wlan0", "eth0", ".hidden"],
        ):
            names = sysfs_probe.sysfs_class("net")
        self.assertEqual(names, ["eth0", "wlan0"])

    def test_sysfs_class_oserror_returns_empty(self):
        def _boom(path):
            raise OSError("no such dir")

        with mock.patch("driverhub.core.probes.sysfs.os.listdir", side_effect=_boom):
            self.assertEqual(sysfs_probe.sysfs_class("block"), [])

    def test_sys_block_fake_paths(self):
        model_suffix = os.path.join("device", "model")
        rotational_suffix = os.path.join("queue", "rotational")

        def fake_read(path):
            sp = str(path)
            if sp.endswith("size"):
                return "5120\n"
            if sp.endswith(model_suffix):
                return "WD Blue\n"
            if sp.endswith(rotational_suffix):
                return "1\n"
            return ""

        with mock.patch(
            "driverhub.core.probes.sysfs.os.listdir",
            return_value=["sda"],
        ), mock.patch("driverhub.core.probes.sysfs._read", side_effect=fake_read):
            disks = sysfs_probe.sys_block()
        self.assertEqual(len(disks), 1)
        disk = disks[0]
        self.assertEqual(disk["name"], "sda")
        self.assertEqual(disk["size_sectors"], 5120)
        self.assertEqual(disk["size_bytes"], 5120 * 512)
        self.assertEqual(disk["model"], "WD Blue")
        self.assertEqual(disk["rotational"], 1)


class UsbIdsTest(unittest.TestCase):
    """Base embutida de IDs USB (probes/usb.py)."""

    def test_usb_vendor_name_known(self):
        self.assertEqual(usb_probe.usb_vendor_name("046d"), "Logitech")
        self.assertEqual(usb_probe.usb_vendor_name("046D"), "Logitech")

    def test_usb_vendor_name_unknown(self):
        self.assertTrue(usb_probe.usb_vendor_name("1234").startswith("Fabricante USB"))

    def test_usb_device_name(self):
        self.assertEqual(usb_probe.usb_device_name("046d", "C539"), "Mouse G502")

    def test_usb_device_name_unknown_falls_back_to_vendor(self):
        self.assertEqual(usb_probe.usb_device_name("046d", "0001"), "Logitech (PID 0001)")

    def test_usb_lookup_tuple(self):
        vendor, device = usb_probe.usb_lookup("046d", "C539")
        self.assertEqual(vendor, "Logitech")
        self.assertEqual(device, "Mouse G502")


class PciIdsTest(unittest.TestCase):
    """Base embutida de IDs PCI (probes/pci.py)."""

    def test_pci_vendor_name(self):
        self.assertEqual(pci_probe.pci_vendor_name("10de"), "NVIDIA")
        self.assertEqual(pci_probe.pci_vendor_name("8086"), "Intel")

    def test_pci_device_name(self):
        self.assertEqual(pci_probe.pci_device_name("10DE", "1E84"), "GeForce RTX 2070 SUPER")

    def test_pci_lookup_tuple(self):
        vendor, device = pci_probe.pci_lookup("10de", "1e84")
        self.assertEqual((vendor, device), ("NVIDIA", "GeForce RTX 2070 SUPER"))


class ModinfoTest(unittest.TestCase):
    """Parâmetro 'modinfo_fields': parser puro 'campo: valor'.

    ``modinfo_fields`` executa o binário ``modinfo`` e só retorna dados em
    Linux; aqui testamos ``_parse_fields`` (função pura) para que a suíte
    rode na plataforma atual sem exigir o binário.
    """

    def test_parse_fields(self):
        text = (
            "filename:       /lib/modules/5.15.0/kernel/drivers/net/wireless/iwlwifi.ko\n"
            "license:        GPL\n"
            "description:    Intel Wireless WiFi driver\n"
        )
        fields = modinfo_probe._parse_fields(text)
        self.assertEqual(fields["license"], "GPL")
        self.assertEqual(fields["description"], "Intel Wireless WiFi driver")
        self.assertTrue(fields["filename"].endswith("iwlwifi.ko"))


class UdevadmTest(unittest.TestCase):
    """Parser do banco do udev (probes/udevadm.py), função pura."""

    def test_parse_export_db(self):
        text = (
            "P: /devices/usb1/1-1\n"
            "N: usb1/1-1\n"
            "E: ID_VENDOR=Logitech\n"
            "E: ID_MODEL=G502\n"
            "\n"
            "P: /devices/pci0/0000:00:1f.6\n"
            "E: ID_NET_NAME=eth0\n"
        )
        devices = udevadm_probe._parse_export_db(text)
        self.assertEqual(len(devices), 2)
        first, second = devices[0], devices[1]
        self.assertEqual(first["path"], "/devices/usb1/1-1")
        self.assertEqual(first["name"], "usb1/1-1")
        self.assertEqual(first["properties"]["ID_VENDOR"], "Logitech")
        self.assertEqual(second["path"], "/devices/pci0/0000:00:1f.6")
        self.assertEqual(second["properties"]["ID_NET_NAME"], "eth0")


class KextstatTest(unittest.TestCase):
    """Parser kextstat (probes/kextstat.py), função pura."""

    def test_parse_kextstat(self):
        line = (
            "  119    0 0xffffff7fbfb93000 0xa000     0x9800     "
            "com.apple.security.sandbox (1.0) 12345678-9ABC-DEF0-1234-56789ABCDEF0\n"
        )
        kexts = kextstat_probe._parse_kextstat(line)
        self.assertEqual(len(kexts), 1)
        kext = kexts[0]
        self.assertEqual(kext["name"], "com.apple.security.sandbox")
        self.assertEqual(kext["version"], "1.0")
        self.assertEqual(kext["kind"], "Sandbox")

    def test_parse_kextstat_ignores_garbage(self):
        lines = (
            "Index Refs Address            Size       Wired      Name (Version) UUID\n"
            "alguma linha sem uuid\n"
        )
        self.assertEqual(kextstat_probe._parse_kextstat(lines), [])


if __name__ == "__main__":
    unittest.main()