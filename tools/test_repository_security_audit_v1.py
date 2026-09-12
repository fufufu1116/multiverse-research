import json
import tempfile
import unittest
from pathlib import Path

from tools.repository_security_audit_v1 import audit


class RepositorySecurityAuditV1Tests(unittest.TestCase):
    def make_registry(self, root: Path, omit=None):
        ids = [
            "GITHUB_CANONICAL", "GOOGLE_DRIVE_RECOVERY", "BUILDKITE_REVIEW", "NETLIFY",
            "TALLY", "AI_PROVIDERS_AND_PLUGINS", "LOCAL_MAC", "FUTURE_CLOUD_RUNTIME"
        ]
        if omit:
            ids.remove(omit)
        payload = {
            "services": [
                {"id": i, "credential_scope": "UNKNOWN_FAIL_CLOSED"} for i in ids
            ]
        }
        p = root / "registry.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_clean_repository_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "safe.md").write_text("no credentials here", encoding="utf-8")
            result = audit(root, self.make_registry(root))
            self.assertEqual(result["critical_count"], 0)
            self.assertEqual(result["decision"], "PASS_NO_CRITICAL_PATTERN_FOUND")
            self.assertFalse(result["write_effects"])
            self.assertEqual(result["runtime"], "OFF")

    def test_private_key_is_critical_and_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "bad.txt").write_text("-----BEGIN PRIVATE KEY-----\nFAKEFAKEFAKE\n", encoding="utf-8")
            result = audit(root, self.make_registry(root))
            finding = next(f for f in result["findings"] if f["type"] == "PRIVATE_KEY")
            self.assertEqual(finding["severity"], "CRITICAL")
            self.assertNotIn("FAKEFAKEFAKE", json.dumps(result))

    def test_github_token_is_detected_without_full_value_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            token = "ghp_" + "A" * 36
            (root / "bad.py").write_text(f"x='{token}'", encoding="utf-8")
            result = audit(root, self.make_registry(root))
            self.assertGreater(result["critical_count"], 0)
            self.assertNotIn(token, json.dumps(result))

    def test_generic_bearer_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "bad.txt").write_text("Authorization: Bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ123456", encoding="utf-8")
            result = audit(root, self.make_registry(root))
            self.assertGreater(result["critical_count"], 0)

    def test_sensitive_filename_is_review_not_critical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env.example").write_text("TOKEN=<set-at-runtime>", encoding="utf-8")
            result = audit(root, self.make_registry(root))
            self.assertTrue(any(f["type"] == "SENSITIVE_PATH_NAME" for f in result["findings"]))
            self.assertEqual(result["critical_count"], 0)

    def test_missing_service_boundary_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = audit(root, self.make_registry(root, omit="TALLY"))
            self.assertEqual(result["decision"], "FAIL_CLOSED")
            self.assertTrue(any(f["type"] == "MISSING_TRUST_BOUNDARY" for f in result["findings"]))

    def test_empty_credential_scope_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = self.make_registry(root)
            data = json.loads(registry.read_text())
            data["services"][0]["credential_scope"] = ""
            registry.write_text(json.dumps(data), encoding="utf-8")
            result = audit(root, registry)
            self.assertTrue(any(f["type"] == "UNKNOWN_CREDENTIAL_SCOPE_UNMARKED" for f in result["findings"]))

    def test_unknown_scope_is_allowed_only_when_explicitly_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = audit(root, self.make_registry(root))
            self.assertEqual(result["registry_state"], "COMPLETE_FOR_V1_DECLARED_SURFACES")


if __name__ == "__main__":
    unittest.main()
