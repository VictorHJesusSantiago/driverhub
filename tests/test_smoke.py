# -*- coding: utf-8 -*-
"""Testes de fumaça — validam módulos essenciais sem alterar o sistema."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driverhub.core import catalog, platform  # noqa: E402
from driverhub.core.actions import run_scan  # noqa: E402
from driverhub.core.database import Database  # noqa: E402


class TestPlatform(unittest.TestCase):
    def test_os_detection(self):
        info = platform.detect_os()
        self.assertIn(info["system"], ("windows", "linux", "darwin"))
        self.assertIn("name", info)
        self.assertIn("arch", info)

    def test_cpu(self):
        cpu = platform.detect_cpu()
        self.assertIn("name", cpu)

    def test_scan_never_crashes(self):
        data = platform.detect_all()
        self.assertIn("os", data)
        self.assertIn("gpu", data)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.path = path
        self.db = Database(path)

    def tearDown(self):
        self.db.close()
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def test_schema_and_seed(self):
        self.assertEqual(self.db.catalog_count(), len(catalog.SEED_CATALOG))
        self.db.log("test", "alvo", "detalhe", True)
        self.assertEqual(len(self.db.history(limit=50)), 1)

    def test_catalog_search(self):
        rows = self.db.catalog_search(term="nvidia")
        self.assertTrue(all("nvidia" in (r["vendor"] + r["device"]).lower() for r in rows))
        self.assertGreaterEqual(len(self.db.catalog_categories()), 5)

    def test_devices_roundtrip(self):
        devices = [{"kind": "gpu", "name": "RTX 4090", "vendor": "NVIDIA",
                    "driver_id": "PCIVEN_10DE", "driver_version": "1.0", "status": "ok"}]
        self.db.save_devices(devices)
        self.assertEqual(self.db.list_devices()[0]["name"], "RTX 4090")

    def test_drivers_roundtrip(self):
        self.db.save_drivers([{"id": "oem0.inf", "name": "nvlt.inf",
                               "provider": "NVIDIA", "version": "1.0",
                               "class": "Display", "status": "installed"}])
        self.assertEqual(self.db.get_driver("oem0.inf")["provider"], "NVIDIA")


class TestActions(unittest.TestCase):
    def test_scan_smoke(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = Database(path)
            data = run_scan(db)
            self.assertIn("drivers", data)
            self.assertIn("os", data)
            # never raises even if pnputil/powershell missing
            db.close()
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


class TestCatalogSanitize(unittest.TestCase):
    def test_only_official_kept(self):
        bad = [{"vendor": "Mall", "category": "outros", "device": "x",
                "url": "https://evil.example.com/driver.exe"}]
        good = [{"vendor": "NVIDIA", "category": "graficos", "device": "y",
                 "url": "https://www.nvidia.com/download"}]
        self.assertEqual(catalog.sanitize_entries(good + bad), [catalog._normalize(good[0])])


if __name__ == "__main__":
    unittest.main(verbosity=2)