import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_continuity_packet.py"
SPEC = importlib.util.spec_from_file_location("build_continuity_packet", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ContinuityPacketTests(unittest.TestCase):
    def _fake_get(self, path):
        if path == "/branches/main":
            return {"commit": {"sha": "main-sha-123"}}
        if path == "/issues/394":
            return {"html_url": "https://github.com/example/394", "title": "control", "state": "open", "updated_at": "2026-09-17T00:00:00Z"}
        if path == "/issues/596":
            return {"html_url": "https://github.com/example/596", "title": "continuity", "state": "open", "updated_at": "2026-09-17T00:00:00Z"}
        if path == "/pulls/595":
            return {"html_url": "https://github.com/example/595", "title": "design", "state": "open", "draft": True, "merged": False}
        if path == "/pulls/597":
            return {
                "html_url": "https://github.com/example/597",
                "title": "candidate",
                "state": "open",
                "draft": True,
                "merged": False,
                "base_sha": "base-sha-456",
                "head_sha": "head-sha-789",
            }
        if path == "/commits?per_page=8":
            return [{"sha": "commit-sha-1", "commit": {"message": "continuity change"}}]
        raise AssertionError(f"unexpected path: {path}")

    def test_packet_contains_fresh_state_and_candidate_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "packet.md"
            stdout = io.StringIO()
            with patch.object(MODULE, "get", side_effect=self._fake_get), patch.dict(
                os.environ, {"GITHUB_TOKEN": "secret-token-for-test"}, clear=False
            ), patch.object(MODULE.sys, "argv", ["build_continuity_packet.py", "--out", str(out)]), redirect_stdout(stdout):
                rc = MODULE.main()

            self.assertEqual(rc, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("main-sha-123", text)
            self.assertIn("PR #597", text)
            self.assertIn("base-sha-456", text)
            self.assertIn("head-sha-789", text)
            self.assertIn("Runtime: `OFF`", text)
            self.assertIn("Fresh Read", text)
            self.assertNotIn("secret-token-for-test", text)

    def test_network_failure_fails_closed_without_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "packet.md"
            stderr = io.StringIO()
            with patch.object(MODULE, "get", side_effect=URLError("offline")), patch.object(
                MODULE.sys, "argv", ["build_continuity_packet.py", "--out", str(out)]
            ), redirect_stderr(stderr):
                rc = MODULE.main()

            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())
            self.assertIn("Fresh Read failed", stderr.getvalue())

    def test_short_truncates_without_splitting_contract(self):
        self.assertEqual(MODULE.short("a" * 10, 5), "aaaa…")
        self.assertEqual(MODULE.short("a   b\n c", 160), "a b c")


if __name__ == "__main__":
    unittest.main()
