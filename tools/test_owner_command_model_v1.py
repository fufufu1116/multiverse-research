import unittest

from tools.owner_command_model_v1 import OwnerCommandError, owner_visible_items, validate_owner_command


def sample_payload():
    return {
        "schema": "MULTIVERSE_OWNER_COMMAND_v1",
        "generated_at": "2026-09-13T17:30:00+09:00",
        "canonical_ref": {
            "backend": "github",
            "locator": "fufufu1116/multiverse-research#432",
            "revision": "e875d491853ab9a27158b617ff185d14ac804039",
        },
        "runtime": "OFF",
        "items": [
            {
                "id": "owner-gate-1",
                "kind": "OWNER_GATE",
                "title": "Perform bounded external action",
                "lane": "CONTROL",
                "status": "NOW",
                "owner_action_required": True,
                "owner_action": {
                    "location": "provider console",
                    "link": "https://example.invalid",
                    "input": "none",
                    "action": "save setting",
                    "reply_with": "done",
                },
                "priority": "P1",
                "authority": "OWNER_GATE_REQUIRED",
                "evidence_refs": ["github:#432"],
            },
            {
                "id": "internal-1",
                "kind": "STATUS",
                "title": "Internal research continues",
                "lane": "SYSTEM_IMPROVEMENT",
                "status": "WAITING",
                "owner_action_required": False,
                "authority": "NONAUTHORITY",
                "evidence_refs": ["github:#432"],
            },
        ],
    }


class OwnerCommandModelV1Tests(unittest.TestCase):
    def test_valid_payload_passes(self):
        self.assertEqual(validate_owner_command(sample_payload())["runtime"], "OFF")

    def test_owner_action_requires_complete_five_part_instruction(self):
        payload = sample_payload()
        del payload["items"][0]["owner_action"]["reply_with"]
        with self.assertRaisesRegex(OwnerCommandError, "owner_action:MISSING:reply_with"):
            validate_owner_command(payload)

    def test_internal_item_cannot_smuggle_owner_action(self):
        payload = sample_payload()
        payload["items"][1]["owner_action"] = {
            "location": "x", "link": "", "input": "", "action": "x", "reply_with": "x"
        }
        with self.assertRaisesRegex(OwnerCommandError, "FORBIDDEN_WITHOUT_OWNER_ACTION"):
            validate_owner_command(payload)

    def test_duplicate_ids_fail_closed(self):
        payload = sample_payload()
        payload["items"][1]["id"] = payload["items"][0]["id"]
        with self.assertRaisesRegex(OwnerCommandError, "DUPLICATE"):
            validate_owner_command(payload)

    def test_owner_view_filters_internal_status_noise(self):
        visible = owner_visible_items(sample_payload())
        self.assertEqual([item["id"] for item in visible], ["owner-gate-1"])


if __name__ == "__main__":
    unittest.main()
