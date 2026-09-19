# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes de catalogação: score/ranking, busca, fontes oficiais, checksum,
manifesto e mescla de entradas. Tudo offline e sem rede (dados fixos e
arquivos temporários locais).
"""

import hashlib
import os
import tempfile
import unittest

from driverhub.core.cataloging import base as cat_base
from driverhub.core.cataloging import diff
from driverhub.core.cataloging import entries as entries_mod
from driverhub.core.cataloging import filter as cfilter
from driverhub.core.cataloging import manifest
from driverhub.core.cataloging import matcher
from driverhub.core.cataloging import sources
from driverhub.core.cataloging import verify
from driverhub.core.cataloging.base import CatalogEntry


class BuiltinEntriesTest(unittest.TestCase):
    """Catálogo embutido (core/cataloging/entries.py)."""

    MIN_ENTRIES = 3

    def test_builtin_entries_non_empty_and_complete(self):
        entries = entries_mod.builtin_entries()
        self.assertGreaterEqual(len(entries), self.MIN_ENTRIES)
        for entry in entries:
            self.assertTrue(entry.vendor, "entry sem vendor")
            self.assertTrue(entry.model, "entry sem model")
            self.assertTrue(entry.version, "entry sem version")
            self.assertTrue(entry.url, "entry sem url")

    def test_builtin_entries_are_official(self):
        entries = entries_mod.builtin_entries()
        self.assertTrue(all(entry.official for entry in entries))


class MatcherTest(unittest.TestCase):
    """score / best_matches (core/cataloging/matcher.py)."""

    NVIDIA_ENTRY = {
        "vendor": "NVIDIA",
        "model": "GeForce RTX 3060",
        "kinds": ["gpu", "graphics", "display"],
        "version": "1.0",
        "url": "https://www.nvidia.com/x",
        "official": True,
    }
    AMD_ENTRY = {
        "vendor": "AMD",
        "model": "Radeon RX 6700 XT",
        "kinds": ["gpu", "graphics", "display"],
        "version": "2.0",
        "url": "https://www.amd.com/x",
        "official": True,
    }
    DEVICE_NVIDIA = {"vendor": "NVIDIA", "model": "GeForce RTX 3060", "class": "gpu"}
    DEVICE_AMD = {"vendor": "AMD", "model": "Radeon RX 6700 XT", "class": "gpu"}

    def test_normalize(self):
        self.assertEqual(matcher.normalize("NVIDIA"), "nvidia")
        self.assertEqual(matcher.normalize("Vídeo"), "video")

    def test_score_better_vendor_model(self):
        nvidia = matcher.score(self.DEVICE_NVIDIA, self.NVIDIA_ENTRY)
        amd = matcher.score(self.DEVICE_NVIDIA, self.AMD_ENTRY)
        # peso model .85 + vendor .75 + class .10*(1/3 de 3 kinds) = 96.1
        self.assertEqual(nvidia, 96.1)
        self.assertGreater(nvidia, amd)

    def test_score_zero_for_unrelated(self):
        unrelated = {"vendor": "Intel", "model": "Wi-Fi 6 AX200", "kinds": ["network"]}
        self.assertEqual(matcher.score(self.DEVICE_NVIDIA, unrelated), 0.0)

    def test_best_matches_ranks(self):
        matches = matcher.best_matches(
            self.DEVICE_NVIDIA,
            [self.AMD_ENTRY, self.NVIDIA_ENTRY],
            top_n=3,
        )
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0].entry.vendor, "NVIDIA")
        self.assertGreaterEqual(matches[0].score, matches[1].score)

    def test_best_matches_top_n(self):
        matches = matcher.best_matches(self.DEVICE_AMD, [self.AMD_ENTRY], top_n=5)
        self.assertEqual(len(matches), 1)


class FilterTest(unittest.TestCase):
    """Busca e filtros do catálogo (core/cataloging/filter.py)."""

    def setUp(self):
        self.entries = [
            CatalogEntry(vendor="NVIDIA", model="GeForce RTX 3060",
                         kinds=["gpu", "graphics"], url="https://www.nvidia.com/x"),
            CatalogEntry(vendor="Intel", model="Wi-Fi 6 AX200",
                         kinds=["network", "wifi"], url="https://www.intel.com/x"),
            CatalogEntry(vendor="Realtek", model="HD Audio Codec",
                         kinds=["audio", "sound"], url="https://www.realtek.com/x"),
        ]

    def test_search_finds_by_model_token(self):
        results = cfilter.search(self.entries, "geforce")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].vendor, "NVIDIA")

    def test_search_empty_text_returns_all(self):
        self.assertEqual(len(cfilter.search(self.entries, "")), 3)

    def test_by_category_ignores_accent_case(self):
        results = cfilter.by_category(self.entries, "GPU")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].vendor, "NVIDIA")

    def test_filter_entries_category_and_query(self):
        results = cfilter.filter_entries(self.entries, category="network", query="wifi")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].vendor, "Intel")


class SourcesTest(unittest.TestCase):
    """Fontes oficiais (core/cataloging/sources.py)."""

    def test_official_host_known_domain(self):
        self.assertEqual(sources.official_host("https://www.nvidia.com/download.aspx"), "nvidia.com")
        self.assertEqual(sources.official_host("https://download.nvidia.com/x"), "nvidia.com")

    def test_official_host_unknown_domain(self):
        self.assertIsNone(sources.official_host("https://evil.example.xyz/driver.exe"))
        self.assertIsNone(sources.official_host(""))

    def test_is_official(self):
        self.assertTrue(sources.is_official("https://www.intel.com/content/www/us/en/download/"))
        self.assertFalse(sources.is_official("http://fake-download.example/d.zip"))
        self.assertFalse(sources.is_official(""))


class VerifyChecksumTest(unittest.TestCase):
    """Verificação de checksum e origem (core/cataloging/verify.py)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "driver.bin")
        self.data = b"dados fixedos do arquivo de driver"
        with open(self.path, "wb") as f:
            f.write(self.data)

    def test_verify_checksum_ok(self):
        digest = hashlib.sha256(self.data).hexdigest()
        self.assertTrue(verify.verify_checksum(self.path, "sha256", digest))

    def test_verify_checksum_wrong(self):
        self.assertFalse(verify.verify_checksum(self.path, "sha256", "0" * 64))

    def test_verify_checksum_missing_file(self):
        self.assertFalse(verify.verify_checksum(os.path.join(self._tmp.name, "nope.bin"), "sha256", "x"))

    def test_is_official(self):
        self.assertTrue(verify.is_official("https://www.intel.com/x"))
        self.assertFalse(verify.is_official("https://evil.example/x"))


class ManifestMergeDiffTest(unittest.TestCase):
    """Manifesto, mescla de entradas e diff de versões."""

    def test_manifest_schema_and_default(self):
        schema = manifest.manifest_schema()
        self.assertEqual(schema["schema_version"], 1)
        default = manifest.default_manifest()
        ok, errors = manifest.validate_manifest(default)
        self.assertTrue(ok, f"manifesto padrão inválido: {errors}")

    def test_validate_manifest_wrong_format(self):
        ok, errors = manifest.validate_manifest({"format": "outro-formato"})
        self.assertFalse(ok)
        self.assertTrue(any("format" in err for err in errors))

    def test_merge_entries_precedence(self):
        merged = cat_base.merge_entries(
            {"vendor": "A", "model": "M", "version": "1", "url": "u1", "official": True, "kinds": ["gpu"]},
            {"version": "2", "url": "u2", "official": True, "kinds": ["graphics"]},
        )
        self.assertEqual(merged.version, "2")
        self.assertEqual(merged.url, "u2")
        self.assertEqual(merged.vendor, "A")
        self.assertIn("gpu", merged.kinds)
        self.assertIn("graphics", merged.kinds)

    def test_merge_entries_official_and(self):
        merged = cat_base.merge_entries({"official": True}, {"official": False})
        self.assertFalse(merged.official)

    def test_diff_versions(self):
        # Observação: diff_versions usa compare(old, new) e classifica old<new
        # como "downgrade" — direção própria desta implementação.
        result = diff.diff_versions("1.0.0", "1.0.1")
        self.assertEqual(result["status"], "downgrade")
        self.assertFalse(result["up_to_date"])
        patch = diff.diff_versions("1.0.1", "1.0.0")
        self.assertEqual(patch["status"], "patch")
        equal = diff.diff_versions("1.2.3", "1.2.3")
        self.assertEqual(equal["status"], "equal")
        self.assertTrue(equal["up_to_date"])


if __name__ == "__main__":
    unittest.main()