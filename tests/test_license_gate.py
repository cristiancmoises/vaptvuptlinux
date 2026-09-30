# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Cristian Cezar Moisés.
"""Catch missing metadata, license drift, and attempts to bypass the kernel gate."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("vv_encoder.c", "vv_decoder.c", "vv_simd.c", "vv_xxh64.c",
           "vv_huffman.c", "vv_ans.c", "vv_bcj.c")


class LicenseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.codec = Path(self.tmp.name) / "codec"
        # Run the actual checker in a controlled package, with synthetic external
        # sources and no dependency on a developer's Git worktree state.
        self.package = Path(self.tmp.name) / "package"
        for relative in ("scripts/check_provenance.py", "tests/page_conformance.c", "Makefile", "PROVENANCE.json"):
            target = self.package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        self.checker = self.package / "scripts/check_provenance.py"
        self.metadata = self.package / "PROVENANCE.json"
        metadata = json.loads(self.metadata.read_text())
        metadata["codec"]["commit"] = None
        self.metadata.write_text(json.dumps(metadata), encoding="utf-8")
        (self.codec / "src").mkdir(parents=True)
        (self.codec / "include").mkdir()
        for source in SOURCES:
            license_id = "BSD-2-Clause" if source == "vv_xxh64.c" else "Apache-2.0"
            (self.codec / "src" / source).write_text(
                f"/* SPDX-License-Identifier: {license_id} */\n", encoding="utf-8")
        (self.codec / "include/vaptvupt.h").write_text(
            '/* SPDX-License-Identifier: Apache-2.0 */\n'
            '#define VV_VERSION_STRING "2.65.13"\n', encoding="utf-8")
        (self.codec / "LICENSE").write_text(
            "Apache License\nVersion 2.0, January 2004\n", encoding="utf-8")
        (self.codec / "NOTICE").write_text(
            "xxHash\nCopyright (c) 2012-2021 Yann Collet\n"
            "Redistribution and use in source and binary forms\n", encoding="utf-8")

    def check(self, mode="userspace"):
        return subprocess.run(
            [sys.executable, str(self.checker), "--codec", str(self.codec), "--mode", mode],
            capture_output=True, text=True, check=False)

    def pin_fixture(self):
        def git(*args):
            return subprocess.run(
                ["git", "-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "core.hooksPath=/dev/null", "-C", str(self.codec), *args],
                capture_output=True, text=True, check=True).stdout.strip()
        git("init", "-b", "main")
        git("add", "src", "include", "LICENSE", "NOTICE")
        git("commit", "--no-gpg-sign", "-m", "Record synthetic test fixture")
        metadata = json.loads(self.metadata.read_text())
        metadata["codec"]["commit"] = git("rev-parse", "HEAD")
        self.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    def test_userspace_accepts_scoped_license_inventory(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_kernel_gate_remains_blocked_for_apache_codec(self):
        result = self.check("kernel")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED", result.stdout)
        self.assertIn("Apache-2.0", result.stdout)

    def test_unknown_license_fails_closed(self):
        (self.codec / "src/vv_encoder.c").write_text(
            "/* SPDX-License-Identifier: GPL-3.0-or-later */\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL", result.stderr)

    def test_missing_spdx_fails_closed(self):
        (self.codec / "src/vv_decoder.c").write_text("/* no declaration */\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_spdx_in_code_string_is_not_a_license_declaration(self):
        (self.codec / "src/vv_decoder.c").write_text(
            'const char *s = "SPDX-License-Identifier: Apache-2.0";\n', encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_symlink_source_fails_closed(self):
        source = self.codec / "src/vv_ans.c"
        source.unlink()
        source.symlink_to(self.codec / "src/vv_encoder.c")
        self.assertEqual(self.check().returncode, 1)

    def test_version_mismatch_fails_closed(self):
        header = self.codec / "include/vaptvupt.h"
        header.write_text(header.read_text().replace("2.65.13", "2.65.11"), encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_header_license_drift_fails_closed(self):
        header = self.codec / "include/vaptvupt.h"
        header.write_text(header.read_text().replace("Apache-2.0", "GPL-3.0-or-later"), encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_multiple_spdx_declarations_fail_closed(self):
        source = self.codec / "src/vv_encoder.c"
        source.write_text(source.read_text() + "/* SPDX-License-Identifier: BSD-2-Clause */\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_missing_notice_fails_closed(self):
        (self.codec / "NOTICE").unlink()
        self.assertEqual(self.check().returncode, 1)

    def test_clean_commit_pin_accepts_scoped_inventory(self):
        self.pin_fixture()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_commit_pin_rejects_a_different_head(self):
        self.pin_fixture()
        metadata = json.loads(self.metadata.read_text())
        metadata["codec"]["commit"] = "1" * 40
        self.metadata.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_commit_pin_rejects_modified_source(self):
        self.pin_fixture()
        source = self.codec / "src/vv_encoder.c"
        source.write_text(source.read_text() + "/* changed */\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_commit_pin_rejects_untracked_header(self):
        self.pin_fixture()
        (self.codec / "include/untracked.h").write_text(
            "/* SPDX-License-Identifier: Apache-2.0 */\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)


if __name__ == "__main__":
    unittest.main()
