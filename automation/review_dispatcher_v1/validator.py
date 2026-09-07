from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.review_dispatcher_v1.model import validate_request

LAB_PIPELINE = (
    REPO_ROOT
    / "buildkite"
    / "review_dispatcher_v1"
    / "MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml"
)
AUDITOR_PIPELINE = (
    REPO_ROOT
    / "buildkite"
    / "review_dispatcher_v1"
    / "MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml"
)
BASELINE = (
    REPO_ROOT
    / "governance"
    / "MULTIVERSE_COMMON_OPERATING_BASELINE_v1.json"
)
CONVERGENCE = (
    REPO_ROOT
    / "governance"
    / "MULTIVERSE_CROSS_CHAT_CAPABILITY_CONVERGENCE_v1.md"
)

SHA40_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")


def _nonauthority() -> dict:
    return {
        "provider_resource_mutation": False,
        "deploy": False,
        "database_mutation": False,
        "provider_effect_enablement": False,
        "runtime_activation_bridge_enablement": False,
        "runtime_activation": False,
        "production_credentials": False,
        "production_deployment": False,
        "protected_data": False,
        "live_business_effect": False,
        "additional_spend": False,
        "merge": False,
        "main_mutation": False,
        "ruleset_mutation": False,
        "workflow_dispatch_rerun": False,
    }


def _sample_request() -> dict:
    return {
        "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
        "request_id": "validator-sample",
        "lane": "LAB",
        "mode": "REPOSITORY_ONLY",
        "repo": "fufufu1116/multiverse-research",
        "pr": 1,
        "head": "a" * 40,
        "tree": "b" * 40,
        "base": "c" * 40,
        "main": "d" * 40,
        "proof_ceiling": "VALIDATOR_SAMPLE_ONLY",
        "execution_state": "VALIDATOR_SAMPLE",
        "supersedes_request_sha256": None,
        "recipe": {
            "subtrees": {},
            "durable_comments": [],
            "source_rules": [],
            "unittest_modules": [],
            "validators": [],
            "secret_scan_paths": [],
            "forbidden_patterns": [],
            "http": None,
        },
        "upstream": {},
        "nonauthority": _nonauthority(),
    }


def validate() -> dict:
    findings: list[str] = []
    checks: dict[str, str] = {}

    required_files = [
        ROOT / "__init__.py",
        ROOT / "model.py",
        ROOT / "dispatcher.py",
        ROOT / "review.py",
        ROOT / "github_app.py",
        ROOT / "publisher.py",
        ROOT / "t2.py",
        ROOT / "test_dispatcher.py",
        ROOT / "README.md",
        LAB_PIPELINE,
        AUDITOR_PIPELINE,
        BASELINE,
        CONVERGENCE,
    ]

    for path in required_files:
        name = f"file:{path.relative_to(REPO_ROOT)}"
        if path.is_file():
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    for path in (
        ROOT / "model.py",
        ROOT / "dispatcher.py",
        ROOT / "review.py",
        ROOT / "github_app.py",
        ROOT / "publisher.py",
        ROOT / "t2.py",
        ROOT / "test_dispatcher.py",
    ):
        name = f"compile:{path.name}"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[name] = "PASS"
        except Exception as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc!r}")

    try:
        validate_request(_sample_request())
        checks["sample_request_validation"] = "PASS"
    except Exception as exc:
        checks["sample_request_validation"] = "FIX_REQUIRED"
        findings.append(f"sample_request_validation: {exc!r}")

    lab = LAB_PIPELINE.read_text()
    auditor = AUDITOR_PIPELINE.read_text()

    for label, text in (
        ("lab", lab),
        ("auditor", auditor),
    ):
        if SHA40_RE.search(text):
            checks[f"{label}:no_job_specific_sha"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:no_job_specific_sha: fixed pipeline contains SHA40"
            )
        else:
            checks[f"{label}:no_job_specific_sha"] = "PASS"

        for forbidden in (
            "onrender.com",
            "DATABASE_URL",
            "reviewed_pr =",
            "reviewed_head =",
            "request_comment =",
        ):
            name = f"{label}:no_job_constant:{forbidden}"
            if forbidden not in text:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: found")

        for required in (
            "git fetch origin main",
            "git archive",
            "dispatcher.py",
            "review.py",
            "review_job.json",
            "review_artifact.json",
            "git init -q .mv_dispatcher_source",
            "JOB_DISPATCHER_REF",
        ):
            name = f"{label}:required:{required}"
            if required in text:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: missing")

        bootstrap_ref = 'DISPATCHER_REF="$(git rev-parse FETCH_HEAD)"'
        if bootstrap_ref in text:
            checks[f"{label}:bootstrap_ref_from_fetch_head"] = "PASS"
        else:
            checks[f"{label}:bootstrap_ref_from_fetch_head"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:bootstrap_ref_from_fetch_head: missing"
            )

        defective_bootstrap_ref = 'git rev-parse origin/main'
        if defective_bootstrap_ref in text:
            checks[f"{label}:no_defective_origin_main_ref"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:no_defective_origin_main_ref: found"
            )
        else:
            checks[f"{label}:no_defective_origin_main_ref"] = "PASS"

        runtime_names = (
            "DISPATCHER_REF",
            "FRESH_DISPATCHER_REF",
            "JOB_DISPATCHER_REF",
            "BUILDKITE_COMMIT",
        )
        unescaped_runtime_vars = []
        for runtime_name in runtime_names:
            escaped = "$$" + runtime_name
            unescaped = "$" + runtime_name
            if unescaped in text.replace(escaped, ""):
                unescaped_runtime_vars.append(unescaped)

        if unescaped_runtime_vars:
            checks[f"{label}:runtime_shell_vars_escaped"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:runtime_shell_vars_escaped: "
                + ",".join(unescaped_runtime_vars)
            )
        else:
            checks[f"{label}:runtime_shell_vars_escaped"] = "PASS"

        for runtime_name in runtime_names:
            escaped = "$$" + runtime_name
            name = f"{label}:runtime_var_present:{runtime_name}"
            if escaped in text:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: missing")

        for required in (
            "rm -f .mv_review_pass",
            "if PYTHONPATH=.mv_dispatcher",
            "touch .mv_review_pass",
            "if [ -f review_artifact.json ]; then",
            "test -f .mv_review_pass",
        ):
            name = f"{label}:failure_artifact_required:{required[:32]}"
            if required in text:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: missing")

        try:
            review_index = text.index("review.py")
            job_upload_index = text.index(
                'buildkite-agent artifact upload \\\n        "review_job.json"'
            )
            artifact_guard_index = text.index(
                "if [ -f review_artifact.json ]; then"
            )
            final_status_index = text.index("test -f .mv_review_pass")
            artifact_order_ok = (
                review_index
                < job_upload_index
                < artifact_guard_index
                < final_status_index
            )
        except ValueError:
            artifact_order_ok = False

        if artifact_order_ok:
            checks[f"{label}:failure_artifact_order"] = "PASS"
        else:
            checks[f"{label}:failure_artifact_order"] = "FIX_REQUIRED"
            findings.append(f"{label}:failure_artifact_order: invalid")

        bundle_name = "review_dispatcher_bundle.tgz"
        if bundle_name in text:
            checks[f"{label}:no_audit_executable_bundle_handoff"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:no_audit_executable_bundle_handoff: found"
            )
        else:
            checks[f"{label}:no_audit_executable_bundle_handoff"] = "PASS"

        trusted_fetch = "git -C .mv_dispatcher_source fetch -q --depth=1 origin main"
        if trusted_fetch in text:
            checks[f"{label}:secret_step_fresh_canonical_fetch"] = "PASS"
        else:
            checks[f"{label}:secret_step_fresh_canonical_fetch"] = "FIX_REQUIRED"
            findings.append(
                f"{label}:secret_step_fresh_canonical_fetch: missing"
            )

    review_source = (ROOT / "review.py").read_text()
    for token in (
        '[sys.executable, "-m", "unittest", module, "-v"]',
        "_run_candidate_process(",
        "_candidate_env(",
        "_repo_file(",
        "latest_exact_current_owner_request(",
        "request_sha256",
        "lab_request_sha256",
        "resolve_public_https_target(base_url)",
        "_PinnedHTTPSConnection(",
    ):
        name = f"review:hardening:{token[:32]}"
        if token in review_source:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    model_source = (ROOT / "model.py").read_text()
    for token in (
        "supersedes_request_sha256",
        "SAME_HEAD_SUPERSESSION_CHAIN_INVALID",
        "sha256_json(request)",
    ):
        name = f"model:request_identity:{token[:32]}"
        if token in model_source:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    if "--lane LAB" in lab:
        checks["lab:lane_fixed"] = "PASS"
    else:
        checks["lab:lane_fixed"] = "FIX_REQUIRED"
        findings.append("lab:lane_fixed: missing")

    if lab.count("checkout:\n      skip: true") == 1:
        checks["lab:publisher_checkout_skipped"] = "PASS"
    else:
        checks["lab:publisher_checkout_skipped"] = "FIX_REQUIRED"
        findings.append("lab:publisher_checkout_skipped: count mismatch")

    if "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY" in lab:
        checks["lab:publisher_key_present"] = "PASS"
    else:
        checks["lab:publisher_key_present"] = "FIX_REQUIRED"
        findings.append("lab:publisher_key_present: missing")

    if "--lane AUDITOR" in auditor:
        checks["auditor:lane_fixed"] = "PASS"
    else:
        checks["auditor:lane_fixed"] = "FIX_REQUIRED"
        findings.append("auditor:lane_fixed: missing")

    if auditor.count("checkout:\n      skip: true") == 2:
        checks["auditor:publisher_t2_checkout_skipped"] = "PASS"
    else:
        checks["auditor:publisher_t2_checkout_skipped"] = "FIX_REQUIRED"
        findings.append(
            "auditor:publisher_t2_checkout_skipped: count mismatch"
        )

    for required in (
        "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
        "publisher.py",
        "t2.py",
        "t2_publish_receipt.json",
    ):
        name = f"auditor:required:{required}"
        if required in auditor:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    baseline = json.loads(BASELINE.read_text())
    expected_baseline = {
        "schema": "MULTIVERSE_COMMON_OPERATING_BASELINE_v1",
        "status": "CANDIDATE_NOT_YET_ADOPTED",
        "baseline_version": "2026-09-07.review-dispatcher-v1",
        "migration_issue": 152,
        "convergence_issue": 93,
        "runtime": "OFF",
    }
    for key, expected in expected_baseline.items():
        name = f"baseline:{key}"
        if baseline.get(key) == expected:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {baseline.get(key)!r} != {expected!r}"
            )

    policy = baseline.get("shared_pipeline_policy") or {}
    if (
        policy.get("during_migration")
        == "single_writer_control_plane_only"
        and policy.get("after_installation")
        == "immutable_shared_pipeline_definition"
        and policy.get("per_chat_step_replacement")
        == "deprecated_after_installation"
    ):
        checks["baseline:pipeline_policy"] = "PASS"
    else:
        checks["baseline:pipeline_policy"] = "FIX_REQUIRED"
        findings.append("baseline:pipeline_policy: mismatch")

    resume = baseline.get("resume_contract") or {}
    if (
        resume.get("fresh_read_required") is True
        and resume.get("read_convergence_issue_93") is True
        and resume.get("consume_latest_adopted_common_baseline") is True
        and resume.get("stale_local_common_procedure_must_yield") is True
    ):
        checks["baseline:resume_contract"] = "PASS"
    else:
        checks["baseline:resume_contract"] = "FIX_REQUIRED"
        findings.append("baseline:resume_contract: mismatch")

    nonauth = baseline.get("nonauthority") or {}
    if nonauth and all(value is False for value in nonauth.values()):
        checks["baseline:nonauthority"] = "PASS"
    else:
        checks["baseline:nonauthority"] = "FIX_REQUIRED"
        findings.append("baseline:nonauthority: not all false")

    convergence = CONVERGENCE.read_text()
    for token in (
        "latest adopted common operating baseline",
        "older chats must stop using the superseded common interface",
        "research chats do not replace Steps",
        "routine review YAML copy/paste count is zero",
        "Runtime remains OFF",
    ):
        name = f"convergence:{token[:30]}"
        if token in convergence:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    return {
        "schema": "MULTIVERSE_REVIEW_DISPATCHER_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "migration_issue": 152,
        "shared_pipeline_mutation_authorized": False,
        "merge_authorized": False,
        "main_mutation_authorized": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))