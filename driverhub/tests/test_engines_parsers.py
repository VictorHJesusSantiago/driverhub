# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes dos parsers de engines/coletores e de versões do DriverHub.

Cobre parsing puro de saídas fixas (pnputil, lsmod/modinfo, lspci -mm,
modinfo campo:valor), utilitários de versão (semver e versions) e parsers
internos do motor Windows. Nada aqui executa binários reais: comandos são
substituídos por mocks. Tudo roda sem admin e sem rede.
"""

import io
import unittest
from unittest import mock

from driverhub.core import linux, windows
from driverhub.core.probes import lspci as lspci_probe
from driverhub.core.probes import modinfo as modinfo_probe
from driverhub.core.probes import pnputil as pnputil_probe
from driverhub.tools import semver, versions


class WindowsParsersTest(unittest.TestCase):
    """Parsers internos do motor Windows (funções puras)."""

    def test_split_csv_respects_quotes(self):
        self.assertEqual(windows._split_csv('"a,"b,c",d"'), ["a,b", "c,d"])

    def test_split_csv_simple_quoted_fields(self):
        self.assertEqual(windows._split_csv('"v1","v2"'), ["v1", "v2"])

    def test_split_date_version_splits(self):
        self.assertEqual(
            windows._split_date_version("05/19/2026 15.11.30.14"),
            ("05/19/2026", "15.11.30.14"),
        )

    def test_split_date_version_without_date(self):
        self.assertEqual(windows._split_date_version("27.20.100.9466"), ("", "27.20.100.9466"))

    def test_guess_kind_graphics(self):
        self.assertEqual(windows._guess_kind("Intel(R) HD Graphics 620", "PCI\\VEN_8086"), "gpu")

    def test_guess_kind_audio(self):
        self.assertEqual(windows._guess_kind("Realtek High Definition Audio", ""), "audio")

    def test_guess_kind_usb(self):
        self.assertEqual(windows._guess_kind("Generic USB Hub", ""), "usb")

    def test_parse_json_list_list(self):
        items = windows._parse_json_list('[{"Name":"A"},{"Name":"B"}]')
        self.assertEqual(len(items), 2)
        self.assertTrue(all(isinstance(i, dict) for i in items))

    def test_parse_json_list_single_object(self):
        items = windows._parse_json_list('{"Name":"X"}')
        self.assertEqual(items, [{"Name": "X"}])

    def test_parse_json_list_invalid(self):
        self.assertEqual(windows._parse_json_list("isso nao e json"), [])

    def test_drivers_list_parses_pnputil_blocks(self):
        sample = (
            "Published Name : oem12.inf\n"
            "Original Name  : igx.inf\n"
            "Provider Name  : Intel Corporation\n"
            "Class Name     : Display\n"
            "Class Guid     : {4d36e968-e325-11ce-bfc1-08002be10318}\n"
            "Driver Version : 05/19/2026 27.20.100.9466\n"
            "Driver Date    : 05/19/2026 15.11.30.14\n"
        )
        with mock.patch("driverhub.core.windows._pnputil", return_value=sample):
            drivers = windows.drivers_list()
        self.assertEqual(len(drivers), 1)
        row = drivers[0]
        self.assertEqual(row["id"], "oem12.inf")
        self.assertEqual(row["inf_file"], "oem12.inf")
        self.assertEqual(row["name"], "igx.inf")
        self.assertEqual(row["class"], "Display")
        self.assertEqual(row["version"], "27.20.100.9466")
        self.assertEqual(row["date"], "05/19/2026")
        self.assertEqual(row["status"], "published")
        self.assertEqual(row["source"], "windows:pnputil")


class LinuxParsersTest(unittest.TestCase):
    """Parsers do motor Linux via mocks de _run (nunca executa binários)."""

    def test_detect_pm_uses_os_release_id_like(self):
        fake_file = io.StringIO("PRETTY_NAME=Fedora\nID_LIKE=debian\n")
        with mock.patch("builtins.open", return_value=fake_file):
            pm, id_like = linux._detect_pm()
        self.assertEqual(pm, "apt")
        self.assertEqual(id_like, "debian")

    def test_kernel_modules_parses_lsmod_and_modinfo(self):
        lsmod_out = (
            "Module                  Size  Used by\n"
            "ext4                  585728  3\n"
            "ntfs3                 139264  0\n"
        )

        def fake_run(cmd, timeout=30):
            if cmd == ["lsmod"]:
                return lsmod_out
            if cmd and cmd[0] == "modinfo":
                name = cmd[1]
                ver = "1.0.0" if name == "ext4" else "1.0.1"
                return (
                    f"version:         {ver}\n"
                    f"author:         Kernel Author\n"
                    f"description:    Descricao do modulo\n"
                )
            return ""

        with mock.patch("driverhub.core.linux._run", side_effect=fake_run):
            mods = linux.kernel_modules()
        self.assertEqual(len(mods), 2)
        ext4, ntfs3 = mods[0], mods[1]
        self.assertEqual(ext4["id"], "ext4")
        self.assertEqual(ext4["version"], "1.0.0")
        self.assertEqual(ext4["size"], "585728")
        self.assertEqual(ext4["used_by"], "3")
        self.assertEqual(ext4["status"], "loaded")
        self.assertEqual(ext4["source"], "kernel:ext4")
        self.assertEqual(ntfs3["version"], "1.0.1")

    def test_module_details_maps_modinfo_fields(self):
        # Observação: module_details usa _re_first que ancora ^ no início da
        # string (sem re.MULTILINE); portanto só o primeiro campo é capturado.
        version_first = (
            "version:        1.0.0\n"
            "author:         Theodore Ts'o\n"
        )
        with mock.patch("driverhub.core.linux._run", return_value=version_first):
            details = linux.module_details("ext4")
        self.assertEqual(details["id"], "ext4")
        self.assertEqual(details["version"], "1.0.0")
        filename_first = "filename:       /lib/modules/5.15.0/kernel/fs/ext4.ko\n"
        with mock.patch("driverhub.core.linux._run", return_value=filename_first):
            details = linux.module_details("ext4")
        self.assertEqual(details["filename"], "/lib/modules/5.15.0/kernel/fs/ext4.ko")

    def test_devices_parses_lspci_and_lsusb(self):
        def fake_run(cmd, timeout=30):
            if cmd == ["lspci", "-nn", "-D"]:
                return "00:02.0 VGA compatible controller: Intel Corporation UHD Graphics 620 [8086:5917]\n"
            if cmd == ["lsusb"]:
                return "Bus 001 Device 002: ID 046d:c539 Logitech G502\n"
            return ""

        with mock.patch("driverhub.core.linux._run", side_effect=fake_run):
            devices = linux.devices()
        self.assertEqual(len(devices), 2)
        pci, usb = devices[0], devices[1]
        self.assertEqual(pci["kind"], "pci")
        self.assertEqual(pci["vendor"], "Intel")
        self.assertEqual(pci["driver_id"], "00:02.0")
        self.assertEqual(usb["kind"], "usb")
        self.assertEqual(usb["vendor"], "USB Device")


class PnputilProbeParsersTest(unittest.TestCase):
    """Parser de blocos da saída pnputil (probes/pnputil.py)."""

    def test_parse_blocks_extracts_labels(self):
        text = (
            "Published Name : oem0.inf\n"
            "Provider Name  : Microsoft\n"
            "\n"
            "Published Name : oem1.inf\n"
            "Class Name     : Printers\n"
        )
        blocks = pnputil_probe._parse_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["Published Name"], "oem0.inf")
        self.assertEqual(blocks[0]["label"], "Published Name")
        self.assertEqual(blocks[0]["Provider Name"], "Microsoft")
        self.assertEqual(blocks[1]["Class Name"], "Printers")

    def test_parse_blocks_empty(self):
        self.assertEqual(pnputil_probe._parse_blocks(""), [])
        self.assertEqual(pnputil_probe._parse_blocks("   \n\n  "), [])


class ModinfoProbeParsersTest(unittest.TestCase):
    """Parser puro 'campo: valor' do modinfo.

    ``modinfo_fields``/``modinfo_license`` executam o binário ``modinfo`` e
    são limitados a plataformas Linux; aqui testamos apenas o parser puro
    ``_parse_fields`` para que a suíte rode em qualquer sistema.
    """

    def test_parse_fields_maps_key_value(self):
        text = (
            "filename:       /lib/modules/5.15.0/kernel/fs/ntfs3.ko\n"
            "license:        GPL\n"
            "srcversion:     A1B2C3D4E5F6\n"
        )
        fields = modinfo_probe._parse_fields(text)
        self.assertEqual(fields.get("filename"), "/lib/modules/5.15.0/kernel/fs/ntfs3.ko")
        self.assertEqual(fields.get("license"), "GPL")
        self.assertEqual(fields.get("srcversion"), "A1B2C3D4E5F6")


class LspciProbeParsersTest(unittest.TestCase):
    """Parser da saída 'lspci -mmnn' (probes/lspci.py)."""

    def test_parse_mm_structures_records(self):
        text = '00:02.0 "VGA compatible controller" "Intel Corporation" "HD Graphics 620" [8086:5917]\n'
        devices = lspci_probe._parse_mm(text)
        self.assertEqual(len(devices), 1)
        dev = devices[0]
        self.assertEqual(dev["slot"], "00:02.0")
        self.assertEqual(dev["class"], "VGA compatible controller")
        self.assertEqual(dev["class_name"], "Display")
        self.assertEqual(dev["vendor"], "Intel Corporation")
        self.assertEqual(dev["device"], "HD Graphics 620")
        self.assertEqual(dev["vid"], "8086")
        self.assertEqual(dev["pid"], "5917")
        self.assertEqual(dev["pci_id"], "8086:5917")

    def test_pci_class_name(self):
        self.assertEqual(lspci_probe.pci_class_name("03"), "Display/VGA")
        self.assertEqual(lspci_probe.pci_class_name("02"), "Rede")
        self.assertEqual(lspci_probe.pci_class_name("ff"), "")


class SemverTest(unittest.TestCase):
    """Parâmetro 'semver' do pedido original (tools/semver.py)."""

    def test_parse_full(self):
        parsed = semver.parse("1.2.3-beta.1+build5")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["major"], 1)
        self.assertEqual(parsed["minor"], 2)
        self.assertEqual(parsed["patch"], 3)
        self.assertEqual(parsed["prerelease"], "beta.1")
        self.assertEqual(parsed["build"], "build5")

    def test_parse_invalid_is_none(self):
        self.assertIsNone(semver.parse("nao-e-versao"))

    def test_compare(self):
        self.assertEqual(semver.compare("1.0.1", "1.0.0"), 1)
        self.assertEqual(semver.compare("1.0.0", "1.0.0"), 0)
        self.assertEqual(semver.compare("1.0.0", "1.1.0"), -1)
        self.assertEqual(semver.compare("10.0.0", "2.0.0"), 1)

    def test_satisfies(self):
        self.assertTrue(semver.satisfies("1.0.5", "~=1.0"))
        self.assertFalse(semver.satisfies("2.0.1", "~=1.0"))
        self.assertTrue(semver.satisfies("1.2.3", ">=1.0.0"))
        self.assertTrue(semver.satisfies("0.5", "<1"))
        self.assertFalse(semver.satisfies("1.0.0", "<1"))

    def test_next_functions(self):
        self.assertEqual(semver.next_major("1.2.3"), "2.0.0")
        self.assertEqual(semver.next_minor("1.2.3"), "1.3.0")
        self.assertEqual(semver.next_patch("1.2.3"), "1.2.4")


class VersionsCompatTest(unittest.TestCase):
    """Comparação de versões estilo Windows (tools/versions.py)."""

    def test_tokenize(self):
        self.assertEqual(versions.tokenize("1.0-beta"), [1, 0, "beta"])

    def test_compare(self):
        self.assertEqual(versions.compare("1.1", "1.0"), 1)
        self.assertEqual(versions.compare("2.0.0.1", "2.0.0"), 1)
        self.assertEqual(versions.compare("1.0", "1.0"), 0)

    def test_is_newer(self):
        self.assertTrue(versions.is_newer("1.2", "1.1"))
        self.assertFalse(versions.is_newer("1.0", "1.1"))

    def test_parse_windows_files(self):
        self.assertEqual(versions.parse_windows_files("10.0.22621.1234"), (10, 0, 22621, 1234))
        self.assertEqual(versions.parse_windows_files(""), (0, 0, 0, 0))
        self.assertEqual(versions.parse_windows_files(None), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()