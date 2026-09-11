from __future__ import annotations

from automation.multimodel_research_v1 import phase_b_live_preauth as _pr305

CANONICAL_MAIN = "d1edc2eabb847c10a4faa59a039b480e85dfb0e4"
CANONICAL_TREE = "488afdff4d5e7b55072ef69baf8dad0056fd3a46"
CANONICAL_MULTIMODEL_SUBTREE = "51f97ee06a81b72932b2a09d2230a19b7ba63a71"
PR305_FROZEN_HEAD = "9662b62107ea29ebc10936ceba172925c3bb7aae"
PR305_FROZEN_TREE = "2375f43d59868169dfa231e78628ccfe20ecc012"
PR313_REQUEST_ARBITRATION_BLOB = "ccf53e79155a79cda4f24a1c03badf3b4d003c97"
PR313_REQUEST_ARBITRATION_TEST_BLOB = "71973ab85f217d018044b1d648516987d89391e1"
PUBLISHER_BLOB = "514505257c04cb5d40cb91d65044c7d3f18d6cb8"
T2_BLOB = "fee70fa6b4cf93455a7f0c04d888be1d5b4bfb2a"
FIXED_LAB_STEPS_BLOB = "2d4ec751dee4e507a08313d403c7d0521c172ae5"
FIXED_AUDITOR_STEPS_BLOB = "c42bae003a3b1dc6d11cf5e6c33996369a4d22d6"


def _bind_fresh_main() -> None:
    _pr305.CANONICAL_MAIN = CANONICAL_MAIN
    _pr305.CANONICAL_TREE = CANONICAL_TREE
    _pr305.CANONICAL_MULTIMODEL_SUBTREE = CANONICAL_MULTIMODEL_SUBTREE


def build_first_live_provider_preauth():
    _bind_fresh_main()
    return _pr305.build_first_live_provider_preauth()


def validate_first_live_provider_preauth(packet):
    _bind_fresh_main()
    return _pr305.validate_first_live_provider_preauth(packet)


def first_live_provider_preauth_sha256(packet):
    _bind_fresh_main()
    return _pr305.first_live_provider_preauth_sha256(packet)


def packet_summary():
    _bind_fresh_main()
    return _pr305.packet_summary()


def classify_pilot_outcome(outcome):
    _bind_fresh_main()
    return _pr305.classify_pilot_outcome(outcome)


def valid_success_fixture():
    _bind_fresh_main()
    return _pr305.valid_success_fixture()


# Preserve the exact PR305 safety constants as the executable successor surface.
PROVIDER = _pr305.PROVIDER
MODEL_ID = _pr305.MODEL_ID
MAX_ATTEMPTS = _pr305.MAX_ATTEMPTS
MAX_INPUT_TOKENS = _pr305.MAX_INPUT_TOKENS
MAX_OUTPUT_TOKENS = _pr305.MAX_OUTPUT_TOKENS
MAX_COST_USD_MICROS = _pr305.MAX_COST_USD_MICROS
PREDECESSOR_PACKET_SHA256 = _pr305.PREDECESSOR_PACKET_SHA256
