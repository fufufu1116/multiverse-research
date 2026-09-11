from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .multiverse_bridge import OpportunityBridgeError, validate_multiverse_review_packet

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"


def validate_bridge_packets() -> dict[str, Any]:
    findings: list[str] = []
    packet_summaries: list[dict[str, str]] = []
    seen_case_ids: set[str] = set()
    seen_packet_hashes: set[str] = set()

    paths = sorted(CASES.glob("review_packet_*.json"))
    if not paths:
        findings.append("NO_REVIEW_PACKET_SPECIMEN")

    for path in paths:
        try:
            packet = json.loads(path.read_text())
            validate_multiverse_review_packet(packet)
        except (json.JSONDecodeError, OpportunityBridgeError, ValueError, RuntimeError) as exc:
            findings.append(f"INVALID_REVIEW_PACKET:{path.name}:{exc}")
            continue

        case_id = packet["case_id"]
        packet_hash = packet["packet_sha256"]
        if case_id in seen_case_ids:
            findings.append(f"DUPLICATE_CASE_ID:{case_id}")
        if packet_hash in seen_packet_hashes:
            findings.append(f"DUPLICATE_PACKET_HASH:{packet_hash}")
        seen_case_ids.add(case_id)
        seen_packet_hashes.add(packet_hash)

        if any(packet["bridge_authority"].values()):
            findings.append(f"BRIDGE_AUTHORITY_NOT_FALSE:{case_id}")
        if packet["research_task"]["constraints"]["network_access"] != "NONE":
            findings.append(f"FROZEN_REVIEW_NETWORK_NOT_NONE:{case_id}")

        packet_summaries.append(
            {
                "file": path.name,
                "case_id": case_id,
                "packet_sha256": packet_hash,
                "task_id": packet["research_task"]["task_id"],
            }
        )

    return {
        "verdict": "PASS" if not findings else "FAIL",
        "findings": findings,
        "packets": packet_summaries,
        "runtime": "OFF",
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_business_effect_authorized": False,
        "canonical_adoption_authorized": False,
    }


def main() -> None:
    print(json.dumps(validate_bridge_packets(), sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
