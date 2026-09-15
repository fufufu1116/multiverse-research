from automation.review_dispatcher_v1.review_ready_adapter_v1 import (
    FAIL, READY, combine, same_identity_payload_consistent,
)


def package(state="PACKAGE_READY_NONAUTHORITY"):
    return {"state": state, "idempotency_key": ["keirin", "CR1_E05"], "authority_created": False, "owner_marker_created": False, "runtime_authority": False}


def transport(state="TRANSPORT_READY_NONAUTHORITY"):
    return {"state": state, "repo": "fufufu1116/multiverse-research", "pr": 569, "head": "0"*40, "tree": "1"*40, "base": "2"*40, "main": "2"*40, "authority_created": False, "owner_marker_created": False, "runtime_authority": False}


def test_both_pass_required():
    assert combine(package(), transport())["state"] == READY
    assert combine(package("PACKAGE_INVALID_FAIL_CLOSED"), transport())["state"] == FAIL
    assert combine(package(), transport("REVIEW_TRANSPORT_REQUIRED"))["state"] == FAIL


def test_authority_flags_fail_closed():
    p=package(); p["authority_created"]=True
    assert combine(p, transport())["state"] == FAIL


def test_same_identity_different_payload_rejected_by_consistency_guard():
    a={"lane_id":"keirin","candidate_id":"CR1_E05","candidate_head":"a"*40,"package_blob_sha":"b"*40,"ready_sha256":"1"*64}
    b=dict(a); b["ready_sha256"]="2"*64
    assert same_identity_payload_consistent(a, b) is False


if __name__ == "__main__":
    test_both_pass_required(); test_authority_flags_fail_closed(); test_same_identity_different_payload_rejected_by_consistency_guard()
    print("REVIEW_READY_ADAPTER_V1_TESTS_PASS:3")
