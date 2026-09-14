import copy
import json
import unittest
from pathlib import Path

from research.opportunity_engine_v0.market_tests.wardrobe_portability_v1.portable_passport import (
    canonical_export,
    recovery_candidates,
    validate_passport,
)


class PortablePassportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample_path = Path(__file__).with_name("synthetic_sample.json")
        cls.sample = json.loads(sample_path.read_text(encoding="utf-8"))

    def test_synthetic_sample_is_valid(self):
        validate_passport(self.sample)

    def test_canonical_export_is_deterministic(self):
        a = canonical_export(self.sample)
        b = canonical_export(copy.deepcopy(self.sample))
        self.assertEqual(a, b)

    def test_recovery_candidate_uses_synthetic_low_wear_review_item(self):
        self.assertEqual(recovery_candidates(self.sample), ("item-002",))

    def test_unknown_item_reference_fails_closed(self):
        altered = copy.deepcopy(self.sample)
        altered["outfits"][0]["item_ids"].append("missing-item")
        with self.assertRaises(ValueError):
            validate_passport(altered)

    def test_duplicate_item_id_fails_closed(self):
        altered = copy.deepcopy(self.sample)
        altered["items"].append(copy.deepcopy(altered["items"][0]))
        with self.assertRaises(ValueError):
            validate_passport(altered)

    def test_user_owned_export_must_be_true(self):
        altered = copy.deepcopy(self.sample)
        altered["user_owned_export"] = False
        with self.assertRaises(ValueError):
            validate_passport(altered)


if __name__ == "__main__":
    unittest.main()
