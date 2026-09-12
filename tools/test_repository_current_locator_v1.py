from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.repository_current_locator_v1 import (
    INDEX_SCHEMA,
    LocatorValidationError,
    build_observed_index,
    validate_registry,
)

REGISTRY_PATH = Path("governance/MULTIVERSE_REPOSITORY_SCOPE_REGISTRY_v1.json")
MAIN_SHA = "e875d491853ab9a27158b617ff185d14ac804039"


def registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


class RepositoryCurrentLocatorTests(unittest.TestCase):
    def test_current_registry_passes_and_is_nonauthority(self):
        result = validate_registry(registry())
        self.assertEqual(result["validation"], "PASS")
        self.assertEqual(result["scope_count"], 6)
        self.assertEqual(result["runtime"], "OFF")
        self.assertEqual(result["authority_role"], "LOCATOR_ONLY_NOT_AUTHORITY_REPLACEMENT")

    def test_duplicate_scope_primary_fails_closed(self):
        value = registry()
        value["scopes"].append(copy.deepcopy(value["scopes"][0]))
        with self.assertRaises(LocatorValidationError):
            validate_registry(value)

    def test_missing_primary_fails_closed(self):
        value = registry()
        del value["scopes"][0]["primary"]
        with self.assertRaises(LocatorValidationError):
            validate_registry(value)

    def test_unknown_scope_fails_closed(self):
        value = registry()
        value["scopes"][0]["scope_id"] = "UNKNOWN_NEW_SCOPE"
        with self.assertRaises(LocatorValidationError):
            validate_registry(value)

    def test_branch_scoped_keirin_pointer_is_preserved(self):
        value = registry()
        keirin = next(s for s in value["scopes"] if s["scope_id"] == "KEIRIN_RESEARCH")
        self.assertEqual(keirin["primary"]["kind"], "repo_path_on_named_branch")
        self.assertEqual(keirin["primary"]["branch"], "research/keirin-real-evidence-dual-lane-20260901-v1")
        self.assertTrue(keirin["primary"]["path"].endswith("KEIRIN_CURRENT_STATE.json"))
        validate_registry(value)

    def test_incomplete_protected_roots_must_fail_closed(self):
        value = registry()
        value["protected_root_policy"]["complete_registry_available"] = False
        value["protected_root_policy"]["state"] = "ASSUMED_COMPLETE"
        with self.assertRaises(LocatorValidationError):
            validate_registry(value)

    def test_bad_observed_main_sha_rejected(self):
        with self.assertRaises(LocatorValidationError):
            build_observed_index(registry(), "stale-main")

    def test_observed_index_is_snapshot_not_authority(self):
        result = build_observed_index(registry(), MAIN_SHA)
        self.assertEqual(result["schema"], INDEX_SCHEMA)
        self.assertEqual(result["canonical_main_observed"], MAIN_SHA)
        self.assertTrue(result["nonauthority"])
        self.assertFalse(result["write_effects"])
        self.assertEqual(result["freshness_rule"], "REVERIFY_ALL_PRIMARY_POINTERS_BEFORE_USE")

    def test_bootstrap_mapping_is_explicit(self):
        value = registry()
        common = next(s for s in value["scopes"] if s["scope_id"] == "COMMON_BOOTSTRAP_GOVERNANCE")
        self.assertEqual(common["primary"]["kind"], "repo_path_on_main")
        self.assertEqual(common["primary"]["path"], "MULTIVERSE_BOOTSTRAP.md")


if __name__ == "__main__":
    unittest.main()
