# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes dos utilitários genéricos (driverhub/tools): Progress, TTLCache,
semver.compare, csvio (roundtrip), tree e retry. Sem rede e sem admin.
"""

import json
import os
import tempfile
import unittest

from driverhub.tools import csvio
from driverhub.tools import retry as retry_mod
from driverhub.tools import semver
from driverhub.tools import tree as tree_mod
from driverhub.tools.cache import TTLCache
from driverhub.tools.progress import Progress


class ProgressTest(unittest.TestCase):
    def test_total_and_clamping(self):
        progress = Progress(10, label="teste")
        self.assertEqual(progress.total, 10)
        progress.update(50)
        self.assertEqual(progress.n, 10)
        progress.update(-5)
        self.assertEqual(progress.n, 0)

    def test_eta_none_when_not_started(self):
        progress = Progress(10)
        self.assertIsNone(progress.eta())

    def test_eta_not_none_after_update(self):
        progress = Progress(10)
        progress.update(5)
        self.assertIsNotNone(progress.eta())

    def test_update_returns_without_rendering_when_not_tty(self):
        progress = Progress(10)
        progress._tty = False
        self.assertIsNone(progress.update(3))


class TTLCacheTest(unittest.TestCase):
    def test_set_get(self):
        cache = TTLCache(ttl=60)
        cache._now = lambda: 1000.0
        cache.set("k", "v")
        self.assertEqual(cache.get("k"), "v")
        self.assertTrue(cache.has("k"))

    def test_expiry_with_mocked_clock(self):
        cache = TTLCache(ttl=60)
        cache._now = lambda: 1000.0
        cache.set("k", "v")
        self.assertEqual(cache.get("k"), "v")
        cache._now = lambda: 1061.0
        self.assertIsNone(cache.get("k"))
        self.assertFalse(cache.has("k"))

    def test_maxsize_eviction(self):
        cache = TTLCache(maxsize=2, ttl=100)
        cache._now = lambda: 1000.0
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        self.assertEqual(cache.size(), 2)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)

    def test_get_or_set(self):
        cache = TTLCache(ttl=60)
        cache._now = lambda: 1000.0
        value, created = cache.get_or_set("x", lambda: 42)
        self.assertEqual(value, 42)
        self.assertTrue(created)
        value, created = cache.get_or_set("x", lambda: 99)
        self.assertEqual(value, 42)
        self.assertFalse(created)

    def test_clear_and_delete(self):
        cache = TTLCache()
        cache._now = lambda: 1000.0
        cache.set("a", 1)
        self.assertTrue(cache.delete("a"))
        self.assertFalse(cache.delete("a"))
        cache.set("b", 2)
        cache.clear()
        self.assertEqual(cache.size(), 0)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cache.json")
            cache = TTLCache(ttl=300)
            cache._now = lambda: 1000.0
            cache.set("k", "v")
            self.assertTrue(cache.save(path))
            loaded = TTLCache()
            loaded._now = lambda: 1000.0
            self.assertEqual(loaded.load(path), 1)
            self.assertEqual(loaded.get("k"), "v")


class SemverCompareTest(unittest.TestCase):
    def test_compare_stable(self):
        self.assertEqual(semver.compare("1.0.1", "1.0.0"), 1)
        self.assertEqual(semver.compare("1.0.0", "1.0.0"), 0)
        self.assertEqual(semver.compare("1.0.0", "2.0.0"), -1)

    def test_compare_invalid_returns_zero(self):
        self.assertEqual(semver.compare("abc", "1.0.0"), 0)


class CsvIOTest(unittest.TestCase):
    def test_roundtrip(self):
        text = csvio.to_csv([["a", "b,c"], ["d", 1]])
        self.assertIn('"b,c"', text)
        rows = csvio.from_csv(text)
        self.assertEqual(rows, [["a", "b,c"], ["d", "1"]])

    def test_from_csv_bytes_with_bom(self):
        rows = csvio.from_csv(b"\xef\xbb\xbfh1,h2\n1,2\n")
        self.assertEqual(rows, [["h1", "h2"], ["1", "2"]])

    def test_from_csv_none(self):
        self.assertEqual(csvio.from_csv(None), [])

    def test_append_and_read_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "saida.csv")
            self.assertTrue(csvio.append_row(path, ["a", "b"]))
            self.assertTrue(csvio.append_row(path, ["c", "d"]))
            rows = csvio.read_rows(path)
            self.assertEqual(rows, [["a", "b"], ["c", "d"]])


class TreeTest(unittest.TestCase):
    def test_tree_renders_box_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "raiz")
            os.makedirs(os.path.join(root, "pasta_a"))
            with open(os.path.join(root, "pasta_a", "arquivo1.txt"), "w") as f:
                f.write("x")
            with open(os.path.join(root, "arquivo2.txt"), "w") as f:
                f.write("y")
            lines = tree_mod.tree(root)
        self.assertGreaterEqual(len(lines), 3)
        self.assertEqual(lines[0], os.path.basename(root))
        joined = "\n".join(lines)
        self.assertIn("\u251c\u2500\u2500 ", joined)  # ├──
        self.assertIn("\u2514\u2500\u2500 ", joined)  # └──

    def test_tree_missing_path(self):
        lines = tree_mod.tree("c:\\caminho\\que\\nao\\existe\\driverhub-test")
        self.assertEqual(len(lines), 1)


class RetryTest(unittest.TestCase):
    def test_retry_succeeds_after_failures(self):
        calls = []

        @retry_mod.retry(times=3, delay=0.0, backoff=1.0)
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("boom")
            return "ok"

        self.assertEqual(flaky(), "ok")
        self.assertEqual(len(calls), 3)

    def test_retry_exhausted_raises(self):
        calls = []

        @retry_mod.retry(times=2, delay=0.0, backoff=1.0)
        def always_fails():
            calls.append(1)
            raise ValueError("sempre falha")

        with self.assertRaises(ValueError):
            always_fails()
        self.assertEqual(len(calls), 2)

    def test_experiment_never_raises(self):
        def flaky():
            raise RuntimeError("falhou")

        result = retry_mod.experiment(flaky, attempts=3, delay=0.0)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["failures"], 3)
        self.assertEqual(result["successes"], 0)


if __name__ == "__main__":
    unittest.main()