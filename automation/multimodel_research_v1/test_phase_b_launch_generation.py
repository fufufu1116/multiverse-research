from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.launch_generation import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    PREDECESSOR_CANDIDATE_SEAL_BLOB,
    REVIEWED_AUDITOR_BUILD,
    REVIEWED_AUDITOR_COMMENT,
    REVIEWED_HEAD,
    REVIEWED_LAB_BUILD,
    REVIEWED_LAB_COMMENT,
    REVIEWED_PR,
    REVIEWED_T1_COMMENT,
    REVIEWED_T2_COMMENT,
    REVIEWED_TEST_COUNT,
    build_current_canonical_launch_generation,
    current_canonical_launch_generation_sha256,
    validate_current_canonical_launch_generation,
)
from automation.multimodel_research_v1.model import (
    ResearchContractError,
    sha256_json,
)
from automation.multimodel_research_v1.phase_b_launch_chain import (
    build_phase_b_current_canonical_launch_chain,
    phase_b_current_canonical_launch_chain_sha256,
    validate_phase_b_current_canonical_launch_chain,
)
from automation.multimodel_research_v1.provider_catalog import (
    validate_provider_catalog,
)
from automation.multimodel_research_v1.test_phase_a import (
    response_schema,
    task_v2,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
OLD_CATALOG = ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
NEW_CATALOG = ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260910.json"
STATIC_GENERATION = ROOT / "PHASE_B_LAUNCH_GENERATION_20260910.json"
HISTORICAL_SEAL = ROOT / "CANDIDATE_SEAL_v1.json"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class PhaseBLaunchGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_snapshot = json.loads(OLD_CATALOG.read_text())
        cls.snapshot = json.loads(NEW_CATALOG.read_text())
        cls.static_generation = json.loads(STATIC_GENERATION.read_text())
        cls.generation = build_current_canonical_launch_generation(
            cls.snapshot
        )
        cls.chain = build_phase_b_current_canonical_launch_chain(
            task_v2(),
            cls.snapshot,
            response_schema(),
            cls.generation,
        )

    def test_479_new_provider_catalog_is_valid(self):
        self.assertEqual(
            validate_provider_catalog(self.snapshot),
            self.snapshot,
        )
        self.assertEqual(
            self.snapshot["snapshot_id"],
            "provider-model-catalog-20260910",
        )

    def test_480_catalog_snapshot_id_date_must_match_observed_date(self):
        broken = copy.deepcopy(self.snapshot)
        broken["snapshot_id"] = "provider-model-catalog-20260909"
        with self.assertRaisesRegex(
            ResearchContractError,
            "CATALOG_SNAPSHOT_ID_DATE_MISMATCH",
        ):
            validate_provider_catalog(broken)

    def test_481_old_20260908_catalog_is_stale_for_current_launch(self):
        with self.assertRaisesRegex(
            ResearchContractError,
            "CATALOG_SNAPSHOT_STALE",
        ):
            build_catalog_freshness_receipt(
                self.old_snapshot,
                checked_at="2026-09-10T11:35:00Z",
            )

    def test_482_new_catalog_is_within_24h_freshness_window(self):
        receipt = build_catalog_freshness_receipt(
            self.snapshot,
            checked_at="2026-09-10T11:35:00Z",
        )
        self.assertEqual(receipt["age_seconds"], 240)
        self.assertEqual(receipt["max_age_seconds"], 86400)
        self.assertIs(receipt["model_catalog_fresh"], True)

    def test_483_historical_pr280_candidate_seal_is_byte_identical(self):
        self.assertEqual(
            _git_blob_sha(HISTORICAL_SEAL),
            "ac4352caead5bbfb3c02658262830407beacec8e",
        )

    def test_484_current_launch_generation_validates_exactly(self):
        self.assertEqual(self.static_generation, self.generation)
        self.assertEqual(
            validate_current_canonical_launch_generation(
                self.snapshot,
                self.generation,
            ),
            self.generation,
        )
        self.assertEqual(
            len(
                current_canonical_launch_generation_sha256(
                    self.snapshot,
                    self.generation,
                )
            ),
            64,
        )

    def test_485_launch_generation_binds_reviewed_pr285_lineage(self):
        value = self.generation
        self.assertEqual(value["reviewed_pr"], REVIEWED_PR)
        self.assertEqual(value["reviewed_head"], REVIEWED_HEAD)
        self.assertEqual(value["reviewed_lab_build"], REVIEWED_LAB_BUILD)
        self.assertEqual(value["reviewed_lab_comment"], REVIEWED_LAB_COMMENT)
        self.assertEqual(value["reviewed_t1_comment"], REVIEWED_T1_COMMENT)
        self.assertEqual(
            value["reviewed_auditor_build"],
            REVIEWED_AUDITOR_BUILD,
        )
        self.assertEqual(
            value["reviewed_auditor_comment"],
            REVIEWED_AUDITOR_COMMENT,
        )
        self.assertEqual(value["reviewed_t2_comment"], REVIEWED_T2_COMMENT)
        self.assertEqual(value["reviewed_test_count"], REVIEWED_TEST_COUNT)

    def test_486_launch_generation_rejects_wrong_canonical_main(self):
        broken = copy.deepcopy(self.generation)
        broken["canonical_main"] = "0" * 40
        with self.assertRaises(ResearchContractError):
            validate_current_canonical_launch_generation(
                self.snapshot,
                broken,
            )

    def test_487_launch_generation_rejects_wrong_canonical_tree(self):
        broken = copy.deepcopy(self.generation)
        broken["canonical_tree"] = "0" * 40
        with self.assertRaises(ResearchContractError):
            validate_current_canonical_launch_generation(
                self.snapshot,
                broken,
            )

    def test_488_launch_generation_rejects_wrong_multimodel_subtree(self):
        broken = copy.deepcopy(self.generation)
        broken["canonical_multimodel_subtree"] = "0" * 40
        with self.assertRaises(ResearchContractError):
            validate_current_canonical_launch_generation(
                self.snapshot,
                broken,
            )

    def test_489_launch_generation_rejects_wrong_predecessor_seal(self):
        broken = copy.deepcopy(self.generation)
        broken["predecessor_candidate_seal_blob"] = "0" * 40
        with self.assertRaises(ResearchContractError):
            validate_current_canonical_launch_generation(
                self.snapshot,
                broken,
            )

    def test_490_launch_generation_rejects_old_catalog_generation(self):
        with self.assertRaises(ResearchContractError):
            validate_current_canonical_launch_generation(
                self.old_snapshot,
                self.generation,
            )

    def test_491_fresh_official_catalog_facts_are_exact(self):
        entries = {
            item["provider"]: item
            for item in self.snapshot["entries"]
        }
        gemini = entries["GOOGLE_GEMINI"]
        claude = entries["ANTHROPIC_CLAUDE"]
        self.assertEqual(gemini["model_id"], "gemini-3.8-flash")
        self.assertEqual(
            gemini["input_usd_micros_per_million_tokens"],
            750000,
        )
        self.assertEqual(
            gemini["output_usd_micros_per_million_tokens"],
            3750000,
        )
        self.assertEqual(gemini["pricing_valid_through"], "2026-12-31")
        self.assertEqual(
            claude["model_id"],
            "claude-haiku-4-5-20251001",
        )
        self.assertEqual(
            claude["input_usd_micros_per_million_tokens"],
            1000000,
        )
        self.assertEqual(
            claude["output_usd_micros_per_million_tokens"],
            5000000,
        )

    def test_492_current_phase_b_launch_chain_validates(self):
        self.assertEqual(
            validate_phase_b_current_canonical_launch_chain(
                task_v2(),
                self.snapshot,
                response_schema(),
                self.generation,
                self.chain,
            ),
            self.chain,
        )
        self.assertEqual(len(self.chain["providers"]), 2)

    def test_493_launch_chain_binds_current_main_subtree_and_catalog(self):
        self.assertEqual(self.chain["canonical_main"], CANONICAL_MAIN)
        self.assertEqual(self.chain["canonical_tree"], CANONICAL_TREE)
        self.assertEqual(
            self.chain["canonical_multimodel_subtree"],
            CANONICAL_MULTIMODEL_SUBTREE,
        )
        self.assertEqual(
            self.chain["predecessor_candidate_seal_blob"],
            PREDECESSOR_CANDIDATE_SEAL_BLOB,
        )
        self.assertEqual(
            self.chain["provider_catalog_snapshot_id"],
            "provider-model-catalog-20260910",
        )
        self.assertEqual(
            self.chain["provider_catalog_snapshot_sha256"],
            sha256_json(self.snapshot),
        )
        self.assertIs(
            self.chain["full_path_rebound_to_launch_generation"],
            True,
        )
        self.assertIs(self.chain["fresh_catalog_bound"], True)

    def test_494_launch_chain_rejects_old_catalog_new_generation_mix(self):
        with self.assertRaises(ResearchContractError):
            validate_phase_b_current_canonical_launch_chain(
                task_v2(),
                self.old_snapshot,
                response_schema(),
                self.generation,
                self.chain,
            )

    def test_495_launch_chain_grants_no_authority_or_live_effect(self):
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "live_provider_execution",
            "protected_data_effect",
            "live_business_effect",
            "adoption_authority",
        ):
            self.assertIs(self.chain[key], False)
        self.assertEqual(self.chain["runtime"], "OFF")
        for provider in self.chain["providers"]:
            for key in (
                "provider_call_authorized",
                "credential_authorized",
                "spend_authorized",
                "live_provider_execution",
                "adoption_authority",
            ):
                self.assertIs(provider[key], False)
            self.assertEqual(provider["runtime"], "OFF")

    def test_496_launch_chain_rejects_generation_digest_tamper(self):
        broken = copy.deepcopy(self.chain)
        broken["launch_generation_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_phase_b_current_canonical_launch_chain(
                task_v2(),
                self.snapshot,
                response_schema(),
                self.generation,
                broken,
            )
        self.assertEqual(
            len(
                phase_b_current_canonical_launch_chain_sha256(
                    task_v2(),
                    self.snapshot,
                    response_schema(),
                    self.generation,
                    self.chain,
                )
            ),
            64,
        )


if __name__ == "__main__":
    unittest.main()
