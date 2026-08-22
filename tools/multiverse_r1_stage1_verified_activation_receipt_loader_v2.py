#!/usr/bin/env python3
"""Hardened production integration guard for the R1 Stage-1 activation receipt.

Pre-activation only. This module adds the three narrow Lab remediations from
PR #66 review comment 5377207648 without provisioning any production state.

Production-facing code must enter through ``load_verified_stage1_context``.
That entrypoint accepts only a repository worktree path; it never accepts
caller-provided activation/authority anchors or an injectable loader/API.
"""
from __future__ import annotations

import argparse
import base64
import inspect
import json
import re
from pathlib import Path
from typing import Any, Mapping

from multiverse_r1_stage1_verified_activation_receipt_loader_v1 import (
    ACTIVATION_RECEIPT_STATUS,
    ActivationReceiptDenied,
    ImmutableActivationReceiptLoader,
    LoadedActivationAnchors,
    _aware_time,
    _canonical_json,
)
from multiverse_r1_stage1_github_runtime_cas_v1 import (
    CANONICAL_REPO,
    STATE_PATH,
    GitHubRuntimeCASLedger,
    _validate_ledger_payload,
)
from multiverse_r1_stage1_canonical_authority_adapter_v1 import (
    CanonicalAuthorityDecisionAdapter,
)
from multiverse_r1_stage1_runtime_v1 import empty_control
from multiverse_r1_state_v1 import empty_state

HARDENING_LAB_COMMENT = 5377207648
EXPECTED_REVIEW_PR = 66
EXPECTED_DEDICATED_CI_NAME = "Multiverse R1 Stage1 Verified Activation Receipt Loader v1 CI"
EXPECTED_FOUNDATION_CI_NAME = "Multiverse Foundation Candidate CI v1"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")

COMMON_REVIEW_FIELDS = {
    "kind",
    "pr_number",
    "id",
    "reviewed_head",
    "reviewed_head_key",
    "verdict_key",
    "verdict",
}
AUDITOR_REVIEW_FIELDS = COMMON_REVIEW_FIELDS | {
    "dedicated_ci_run_id",
    "dedicated_ci_name",
    "foundation_ci_run_id",
    "foundation_ci_name",
}

_CONTEXT_SEAL = object()


class ProductionIntegrationDenied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise ProductionIntegrationDenied(code)


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _strict_json_string(value: Any, *, fields: set[str], code: str) -> dict:
    if not isinstance(value, str) or not value:
        _deny(code)
    try:
        decoded = json.loads(value)
    except Exception as exc:
        raise ProductionIntegrationDenied(code) from exc
    if not isinstance(decoded, dict) or set(decoded) != fields:
        _deny(code)
    if value != _canonical_json(decoded):
        _deny(code + "_NOT_CANONICAL_JSON")
    return decoded


def _validate_review_descriptor(value: Mapping[str, Any], *, auditor: bool) -> None:
    if value.get("kind") not in {"ISSUE_COMMENT", "PULL_REQUEST_REVIEW"}:
        _deny("ACTIVATION_FINAL_REVIEW_KIND")
    if value.get("pr_number") != EXPECTED_REVIEW_PR:
        _deny("ACTIVATION_FINAL_REVIEW_PR")
    if not _positive_int(value.get("id")):
        _deny("ACTIVATION_FINAL_REVIEW_ID")
    if not isinstance(value.get("reviewed_head"), str) or not _HEX40.fullmatch(value["reviewed_head"]):
        _deny("ACTIVATION_FINAL_REVIEW_HEAD")
    for key in ("reviewed_head_key", "verdict_key"):
        if not isinstance(value.get(key), str) or not value[key]:
            _deny("ACTIVATION_FINAL_REVIEW_FIELD_KEY")
    if value.get("verdict") != "PASS":
        _deny("ACTIVATION_FINAL_REVIEW_VERDICT_NOT_PASS")
    if auditor:
        if not _positive_int(value.get("dedicated_ci_run_id")) or not _positive_int(value.get("foundation_ci_run_id")):
            _deny("ACTIVATION_FINAL_CI_RUN_ID")
        if value.get("dedicated_ci_name") != EXPECTED_DEDICATED_CI_NAME:
            _deny("ACTIVATION_FINAL_DEDICATED_CI_NAME")
        if value.get("foundation_ci_name") != EXPECTED_FOUNDATION_CI_NAME:
            _deny("ACTIVATION_FINAL_FOUNDATION_CI_NAME")


def _body_has_exact_field(body: str, key: str, value: str) -> bool:
    wanted = f"{key}: {value}"
    return any(line.strip().strip("`") == wanted for line in body.splitlines())


def _verify_review_object(base: ImmutableActivationReceiptLoader, desc: Mapping[str, Any]) -> None:
    pr = desc["pr_number"]
    rid = desc["id"]
    if desc["kind"] == "ISSUE_COMMENT":
        _, obj = base._api(f"/repos/{CANONICAL_REPO}/issues/comments/{rid}")
        if not isinstance(obj, dict):
            _deny("ACTIVATION_FINAL_REVIEW_OBJECT")
        issue_url = obj.get("issue_url")
        if not isinstance(issue_url, str) or not issue_url.endswith(f"/issues/{pr}"):
            _deny("ACTIVATION_FINAL_REVIEW_PR_MISMATCH")
        body = obj.get("body")
        if not isinstance(body, str):
            _deny("ACTIVATION_FINAL_REVIEW_BODY")
    else:
        _, obj = base._api(f"/repos/{CANONICAL_REPO}/pulls/{pr}/reviews/{rid}")
        if not isinstance(obj, dict):
            _deny("ACTIVATION_FINAL_REVIEW_OBJECT")
        if obj.get("commit_id") != desc["reviewed_head"]:
            _deny("ACTIVATION_FINAL_REVIEW_COMMIT_ID")
        body = obj.get("body")
        if not isinstance(body, str):
            _deny("ACTIVATION_FINAL_REVIEW_BODY")
    if not _body_has_exact_field(body, desc["reviewed_head_key"], desc["reviewed_head"]):
        _deny("ACTIVATION_FINAL_REVIEW_HEAD_NOT_IN_EVIDENCE")
    if not _body_has_exact_field(body, desc["verdict_key"], "PASS"):
        _deny("ACTIVATION_FINAL_REVIEW_PASS_NOT_IN_EVIDENCE")


def _verify_ci_run(
    base: ImmutableActivationReceiptLoader,
    *,
    run_id: int,
    expected_name: str,
    expected_head: str,
) -> None:
    _, run = base._api(f"/repos/{CANONICAL_REPO}/actions/runs/{run_id}")
    if not isinstance(run, dict):
        _deny("ACTIVATION_FINAL_CI_OBJECT")
    if run.get("name") != expected_name:
        _deny("ACTIVATION_FINAL_CI_NAME")
    if run.get("head_sha") != expected_head:
        _deny("ACTIVATION_FINAL_CI_HEAD")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        _deny("ACTIVATION_FINAL_CI_NOT_SUCCESS")
    if run.get("event") != "pull_request":
        _deny("ACTIVATION_FINAL_CI_EVENT")


def _verify_final_review_and_ci_evidence(
    base: ImmutableActivationReceiptLoader,
    receipt: Mapping[str, Any],
) -> str:
    gov = receipt.get("governance_evidence")
    if not isinstance(gov, dict):
        _deny("ACTIVATION_FINAL_GOVERNANCE_EVIDENCE")
    lab = _strict_json_string(
        gov.get("final_lab_evidence_ref"), fields=COMMON_REVIEW_FIELDS,
        code="ACTIVATION_FINAL_LAB_EVIDENCE_SCHEMA",
    )
    auditor = _strict_json_string(
        gov.get("final_auditor_evidence_ref"), fields=AUDITOR_REVIEW_FIELDS,
        code="ACTIVATION_FINAL_AUDITOR_EVIDENCE_SCHEMA",
    )
    _validate_review_descriptor(lab, auditor=False)
    _validate_review_descriptor(auditor, auditor=True)
    if lab["reviewed_head"] != auditor["reviewed_head"]:
        _deny("ACTIVATION_FINAL_REVIEW_HEAD_DISAGREEMENT")
    reviewed_head = lab["reviewed_head"]
    runtime = receipt.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("audited_implementation_head") != reviewed_head:
        _deny("ACTIVATION_AUDITED_IMPLEMENTATION_HEAD_NOT_FINAL_REVIEW_HEAD")

    _, pr_obj = base._api(f"/repos/{CANONICAL_REPO}/pulls/{EXPECTED_REVIEW_PR}")
    if not isinstance(pr_obj, dict):
        _deny("ACTIVATION_FINAL_REVIEW_PR_OBJECT")
    head_obj = pr_obj.get("head")
    if not isinstance(head_obj, dict) or head_obj.get("sha") != reviewed_head:
        _deny("ACTIVATION_FINAL_REVIEW_PR_HEAD_DRIFT")

    _verify_review_object(base, lab)
    _verify_review_object(base, auditor)
    _verify_ci_run(
        base,
        run_id=auditor["dedicated_ci_run_id"],
        expected_name=auditor["dedicated_ci_name"],
        expected_head=reviewed_head,
    )
    _verify_ci_run(
        base,
        run_id=auditor["foundation_ci_run_id"],
        expected_name=auditor["foundation_ci_name"],
        expected_head=reviewed_head,
    )
    return reviewed_head


def _decode_api_file(payload: Any, code: str) -> bytes:
    if not isinstance(payload, dict) or payload.get("type") != "file":
        _deny(code)
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        _deny(code + "_ENCODING")
    try:
        return base64.b64decode("".join(payload["content"].split()), validate=True)
    except Exception as exc:
        raise ProductionIntegrationDenied(code + "_DECODE") from exc


def _verify_exact_initial_ledger(
    base: ImmutableActivationReceiptLoader,
    receipt: Mapping[str, Any],
) -> None:
    runtime = receipt.get("runtime")
    if not isinstance(runtime, dict):
        _deny("ACTIVATION_GENESIS_RUNTIME_SCHEMA")
    head = runtime.get("initial_ledger_head")
    genesis = runtime.get("runtime_genesis")
    if not isinstance(head, str) or not _HEX40.fullmatch(head):
        _deny("ACTIVATION_GENESIS_HEAD")
    if not isinstance(genesis, str) or not _HEX40.fullmatch(genesis):
        _deny("ACTIVATION_GENESIS_PARENT")

    _, commit = base._api(f"/repos/{CANONICAL_REPO}/commits/{head}")
    if not isinstance(commit, dict) or commit.get("sha") != head:
        _deny("ACTIVATION_GENESIS_COMMIT_OBJECT")
    parents = commit.get("parents")
    if (
        not isinstance(parents, list)
        or len(parents) != 1
        or not isinstance(parents[0], dict)
        or parents[0].get("sha") != genesis
    ):
        _deny("ACTIVATION_GENESIS_MUST_BE_SINGLE_CHILD_OF_CANONICAL_MAIN")
    files = commit.get("files")
    if not isinstance(files, list) or {x.get("filename") for x in files if isinstance(x, dict)} != {STATE_PATH}:
        _deny("ACTIVATION_GENESIS_COMMIT_SCOPE")

    _, file_obj = base._api(
        f"/repos/{CANONICAL_REPO}/contents/{STATE_PATH}?ref={head}"
    )
    raw = _decode_api_file(file_obj, "ACTIVATION_GENESIS_LEDGER_FILE")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ProductionIntegrationDenied("ACTIVATION_GENESIS_LEDGER_JSON") from exc
    try:
        _validate_ledger_payload(payload)
    except Exception as exc:
        raise ProductionIntegrationDenied("ACTIVATION_GENESIS_LEDGER_INVALID:" + str(exc)) from exc
    if payload.get("sequence") != 0 or payload.get("transition_auth") is not None:
        _deny("ACTIVATION_GENESIS_NOT_SEQUENCE_ZERO")

    activated_at = _aware_time(
        receipt["activation_window"]["activated_at"],
        "ACTIVATION_GENESIS_ACTIVATED_AT",
    )
    expected_control = empty_control(
        activation_receipt_id=receipt["activation_receipt_id"],
        canonical_main=receipt["canonical_main"],
        audited_implementation_head=runtime["audited_implementation_head"],
        runtime_genesis=runtime["runtime_genesis"],
        activated_at=activated_at,
    )
    if payload.get("control") != expected_control:
        _deny("ACTIVATION_GENESIS_CONTROL_NOT_EXACT_EMPTY_CONTROL")
    if payload.get("r1_state") != empty_state():
        _deny("ACTIVATION_GENESIS_R1_STATE_NOT_EMPTY")


class VerifiedStage1ProductionContext:
    """Opaque production integration product. No caller-supplied anchors accepted."""

    __slots__ = ("__repo_root", "__runtime_anchor", "__authority_anchor", "__seal")

    def __init__(
        self,
        *,
        repo_root: Path,
        loaded: LoadedActivationAnchors,
        _seal: object,
    ) -> None:
        if _seal is not _CONTEXT_SEAL or type(loaded) is not LoadedActivationAnchors:
            _deny("ACTIVATION_PRODUCTION_CONTEXT_NOT_LOADER_MINTED")
        self.__repo_root = Path(repo_root).resolve()
        self.__runtime_anchor = loaded.runtime
        self.__authority_anchor = loaded.authority
        self.__seal = _seal

    def build_runtime_ledger(self, *, writer_auth_key: bytes) -> GitHubRuntimeCASLedger:
        if self.__seal is not _CONTEXT_SEAL:
            _deny("ACTIVATION_PRODUCTION_CONTEXT_SEAL")
        return GitHubRuntimeCASLedger(
            self.__repo_root,
            activation_anchor=self.__runtime_anchor,
            writer_auth_key=writer_auth_key,
        )

    def build_authority_adapter(self) -> CanonicalAuthorityDecisionAdapter:
        if self.__seal is not _CONTEXT_SEAL:
            _deny("ACTIVATION_PRODUCTION_CONTEXT_SEAL")
        return CanonicalAuthorityDecisionAdapter(
            self.__repo_root,
            anchor=self.__authority_anchor,
        )


class FinalVerifiedStage1ProductionLoader:
    """Non-subclassable sole production integration loader."""

    __slots__ = ("_repo_root",)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del kwargs
        raise TypeError("FinalVerifiedStage1ProductionLoader cannot be subclassed")

    def __init__(self, repo_root: Path | str) -> None:
        self._repo_root = Path(repo_root).resolve()

    def load(self) -> VerifiedStage1ProductionContext:
        # Exact base type is constructed internally. Callers cannot inject a subclass,
        # fake API adapter, or preconstructed anchor into this production entrypoint.
        base = ImmutableActivationReceiptLoader(self._repo_root)
        if type(base) is not ImmutableActivationReceiptLoader:
            _deny("ACTIVATION_BASE_LOADER_TYPE_DRIFT")
        try:
            loaded = base.load()
        except ActivationReceiptDenied as exc:
            raise ProductionIntegrationDenied("ACTIVATION_BASE_RECEIPT_DENIED:" + str(exc)) from exc
        if type(loaded) is not LoadedActivationAnchors:
            _deny("ACTIVATION_BASE_LOADER_PRODUCT_TYPE")
        receipt = loaded.receipt
        if not isinstance(receipt, dict) or receipt.get("status") != ACTIVATION_RECEIPT_STATUS:
            _deny("ACTIVATION_BASE_RECEIPT_PRODUCT")

        _verify_exact_initial_ledger(base, receipt)
        reviewed_head = _verify_final_review_and_ci_evidence(base, receipt)
        if loaded.runtime.audited_implementation_head != reviewed_head:
            _deny("ACTIVATION_RUNTIME_ANCHOR_REVIEW_HEAD_DRIFT")

        main_after, trusted_now = base._fresh_main()
        if main_after != receipt["canonical_main"]:
            _deny("ACTIVATION_POST_HARDENING_MAIN_DRIFT")
        expires_at = _aware_time(
            receipt["activation_window"]["expires_at"],
            "ACTIVATION_POST_HARDENING_EXPIRES_AT",
        )
        activated_at = _aware_time(
            receipt["activation_window"]["activated_at"],
            "ACTIVATION_POST_HARDENING_ACTIVATED_AT",
        )
        if trusted_now < activated_at or trusted_now >= expires_at:
            _deny("ACTIVATION_POST_HARDENING_OUTSIDE_TRUSTED_WINDOW")

        return VerifiedStage1ProductionContext(
            repo_root=self._repo_root,
            loaded=loaded,
            _seal=_CONTEXT_SEAL,
        )


def load_verified_stage1_context(repo_root: Path | str) -> VerifiedStage1ProductionContext:
    """Sole production integration entrypoint; no anchors/API objects are injectable."""
    return FinalVerifiedStage1ProductionLoader(repo_root).load()


def selftest() -> None:
    # Fix 1: caller-supplied anchor objects are not parameters of the production entrypoint.
    sig = inspect.signature(load_verified_stage1_context)
    assert list(sig.parameters) == ["repo_root"]
    try:
        VerifiedStage1ProductionContext(
            repo_root=Path("."), loaded=object(), _seal=object()  # type: ignore[arg-type]
        )
        raise AssertionError("manual production context unexpectedly accepted")
    except ProductionIntegrationDenied:
        pass
    try:
        class _FakeFinalLoader(FinalVerifiedStage1ProductionLoader):
            pass
        raise AssertionError("subclassable production loader")
    except TypeError:
        pass
    print("CALLER_CONSTRUCTED_ANCHOR_NOT_ACCEPTED_BY_PRODUCTION_ENTRYPOINT")
    print("FAKE_OR_SUBCLASSED_LOADER_CANNOT_REACH_PRODUCTION_ENTRYPOINT")

    # Fix 2: exact genesis validator rejects non-zero and nonempty-state payload shapes.
    # Pure invariants are asserted here; live GitHub object verification occurs in load().
    genesis = {
        "schema_version": "MULTIVERSE_R1_STAGE1_GITHUB_RUNTIME_LEDGER_v3",
        "sequence": 0,
        "control": {},
        "r1_state": empty_state(),
        "transition_auth": None,
    }
    assert genesis["sequence"] == 0 and genesis["transition_auth"] is None
    assert genesis["r1_state"] == empty_state()
    print("INITIAL_LEDGER_SEQUENCE_ZERO_AND_EMPTY_STATE_REQUIRED")

    # Fix 3: evidence fields are canonical structured JSON, not decorative strings.
    head = "a" * 40
    lab = {
        "kind": "ISSUE_COMMENT",
        "pr_number": 66,
        "id": 1,
        "reviewed_head": head,
        "reviewed_head_key": "LAB_REVIEWED_HEAD",
        "verdict_key": "LAB_VERIFIED_RECEIPT_LOADER_VERDICT",
        "verdict": "PASS",
    }
    auditor = {
        **lab,
        "kind": "PULL_REQUEST_REVIEW",
        "id": 2,
        "reviewed_head_key": "AUDITOR_REVIEWED_HEAD",
        "verdict_key": "AUDITOR_VERIFIED_RECEIPT_LOADER_VERDICT",
        "dedicated_ci_run_id": 3,
        "dedicated_ci_name": EXPECTED_DEDICATED_CI_NAME,
        "foundation_ci_run_id": 4,
        "foundation_ci_name": EXPECTED_FOUNDATION_CI_NAME,
    }
    lab2 = _strict_json_string(_canonical_json(lab), fields=COMMON_REVIEW_FIELDS, code="SELFTEST_LAB")
    auditor2 = _strict_json_string(_canonical_json(auditor), fields=AUDITOR_REVIEW_FIELDS, code="SELFTEST_AUDITOR")
    _validate_review_descriptor(lab2, auditor=False)
    _validate_review_descriptor(auditor2, auditor=True)
    try:
        _strict_json_string("decorative-text", fields=COMMON_REVIEW_FIELDS, code="SELFTEST_DECORATIVE")
        raise AssertionError("decorative evidence accepted")
    except ProductionIntegrationDenied:
        pass
    print("FINAL_LAB_AUDITOR_AND_CI_EVIDENCE_STRUCTURED_AND_PINNED")
    print("AUDITED_IMPLEMENTATION_HEAD_MUST_EQUAL_FINAL_REVIEWED_HEAD")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    print("PRODUCTION_PROVISIONING_PERFORMED=false")
    print("MULTIVERSE_R1_STAGE1_VERIFIED_RECEIPT_HARDENING_V2_SELFTEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    parser.error("pre-activation production-integration guard only; use --selftest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
