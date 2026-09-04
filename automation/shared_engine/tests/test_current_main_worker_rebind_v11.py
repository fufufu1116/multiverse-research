from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "automation/shared_engine/CURRENT_MAIN_WORKER_REBIND_V11.json"

EXPECTED = {
    "automation/shared_engine/local_persistent_worker_v9.py": "6056c50759147bd3a306bb6f71d54bb354ab7b60",
    "automation/shared_engine/tests/test_local_persistent_worker_v9.py": "9185be3271f5e0b6a631cfce2830a7bceafea2cc",
    "automation/shared_engine/tests/test_local_persistent_worker_v9_integration.py": "a256521162a46353519c0233a360c43fd48e09e6",
    "automation/shared_engine/process_isolated_worker_broker_v10.py": "54991d33e9ea8e9126fa51285483fa557799f72d",
    "automation/shared_engine/process_isolated_worker_v10.py": "9d65c61cbaf537064f95fc5489753664693974d0",
    "automation/shared_engine/tests/v10_test_process_isolated_worker.py": "134a1ccc40038a089cf58e69f4cb2f90efdc7fc7",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

class CurrentMainWorkerRebindV11Test(unittest.TestCase):
    def test_exact_imported_functional_blob_identity(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(manifest["imported_exact_git_blobs"], EXPECTED)
        for rel, expected in EXPECTED.items():
            self.assertEqual(git_blob_sha((ROOT / rel).read_bytes()), expected, rel)

    def test_current_main_and_v7_contract_are_distinct_by_design(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(manifest["base_canonical_main"], "a6f56facc80709f2e7b8218d927484d522bfa356")
        self.assertEqual(manifest["reviewed_pr91_tree"], manifest["base_canonical_main_tree"])
        self.assertEqual(manifest["inherited_v7_contract_main"], "040d37f0a4e426cf2e119706484c90cbb48f0e56")
        self.assertNotEqual(manifest["base_canonical_main"], manifest["inherited_v7_contract_main"])
        canonical = (ROOT / "automation/shared_engine/canonical_v7_binding.py").read_text()
        self.assertIn('CANONICAL_MAIN="040d37f0a4e426cf2e119706484c90cbb48f0e56"', canonical)
        self.assertIn('V7_HEAD="4a72ef46116043094c7a8e494404956925a5b3bf"', canonical)

    def test_no_effect_authority(self):
        a = json.loads(MANIFEST.read_text())["architecture"]
        for key in ("live_provider", "network_provider", "external_effect", "spend", "secret_credential", "runtime"):
            self.assertIs(a[key], False, key)
        self.assertIs(a["workflow_authority_remains_pr91_sqlite"], True)
        self.assertIs(a["inherited_pr91_files_modified"], False)
        self.assertIs(a["inherited_v7_contract_rebound"], False)

if __name__ == "__main__":
    unittest.main()
