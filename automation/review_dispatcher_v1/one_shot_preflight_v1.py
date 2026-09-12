from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Callable

PREFLIGHT_SCHEMA = "MULTIVERSE_ONE_SHOT_PREFLIGHT_v1"
FIXED_JOB_SCHEMA = "MULTIVERSE_FIXED_REVIEW_JOB_v1"
FIXED_ARTIFACT_SCHEMA = "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1"

FORBIDDEN_FIRST_STEP_ENV = (
    "DATABASE_URL",
    "RENDER_API_KEY",
    "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
    "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
)


def _tail(text: str | None, *, lines: int = 24) -> str:
    values = (text or "").splitlines()
    return "\n".join(values[-lines:])


def _failure_class(stdout: str | None, stderr: str | None) -> str:
    text = f"{stdout or ''}\n{stderr or ''}".lower()
    if (
        ("http error 403" in text or "http error 429" in text)
        and "rate limit" in text
    ):
        return "INFRA_GITHUB_READ_RATE_LIMIT"
    if "dispatcher_fix_required:" in text:
        return "DISPATCHER_CONTRACT_FAILURE"
    return "DISPATCHER_EXECUTION_FAILURE"


def _safe_extract_tar(tar_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(tar_path, "r") as archive:
        for member in archive.getmembers():
            member_path = (destination / member.name).resolve()
            try:
                member_path.relative_to(destination)
            except ValueError as exc:
                raise RuntimeError(
                    f"PREFLIGHT_ARCHIVE_PATH_ESCAPE:{member.name}"
                ) from exc
        archive.extractall(destination)


def _result(
    *,
    ready: bool,
    classification: str,
    dispatcher_ref: str,
    head: str,
    lane: str,
    repo: str,
    job: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    findings: list[str] | None = None,
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> dict[str, Any]:
    return {
        "schema": PREFLIGHT_SCHEMA,
        "ready": ready,
        "state": "ONE_SHOT_PREFLIGHT_READY" if ready else "ONE_SHOT_PREFLIGHT_BLOCKED",
        "classification": classification,
        "repo": repo,
        "lane": lane,
        "head": head,
        "dispatcher_ref": dispatcher_ref,
        "request_id": (job or {}).get("request_id"),
        "request_comment": (job or {}).get("request_comment"),
        "request_sha256": (job or {}).get("request_sha256"),
        "tree": (job or {}).get("tree"),
        "base": (job or {}).get("base"),
        "main": (job or {}).get("main"),
        "review_verdict": (artifact or {}).get("verdict"),
        "test_count": (artifact or {}).get("test_count"),
        "findings": list(findings or (artifact or {}).get("findings") or []),
        "artifact_serialization": (
            "PASS" if artifact is not None else "NOT_REACHED"
        ),
        "publication_attempted": False,
        "owner_build_consumed": False,
        "runtime": "OFF",
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def classify_review_outcome(
    *,
    returncode: int,
    artifact: dict[str, Any] | None,
) -> tuple[bool, str, list[str]]:
    if artifact is None:
        return False, "REVIEW_ARTIFACT_MISSING_OR_INVALID", []
    if artifact.get("schema_version") != FIXED_ARTIFACT_SCHEMA:
        return False, "REVIEW_ARTIFACT_SCHEMA_MISMATCH", [
            f"schema_version:{artifact.get('schema_version')!r}"
        ]
    findings = artifact.get("findings")
    if not isinstance(findings, list):
        return False, "REVIEW_ARTIFACT_FINDINGS_INVALID", [
            "findings:not-list"
        ]
    verdict = artifact.get("verdict")
    if returncode == 0 and verdict == "PASS" and findings == []:
        return True, "PASS", []
    if verdict == "FIX_REQUIRED" or findings:
        return False, "REVIEW_RECIPE_OR_CANDIDATE_FAILURE", list(findings)
    return False, "REVIEW_EXECUTION_FAILURE", list(findings)


def run_one_shot_preflight(
    *,
    dispatcher_ref: str,
    lane: str,
    repo: str,
    head: str,
    repo_root: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if lane not in ("LAB", "AUDITOR"):
        return _result(
            ready=False,
            classification="PREFLIGHT_LANE_INVALID",
            dispatcher_ref=dispatcher_ref,
            head=head,
            lane=lane,
            repo=repo,
        )

    root = repo_root.resolve()
    local = command_runner(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        text=True,
        capture_output=True,
    )
    if local.returncode != 0 or local.stdout.strip() != head:
        return _result(
            ready=False,
            classification="LOCAL_HEAD_MISMATCH",
            dispatcher_ref=dispatcher_ref,
            head=head,
            lane=lane,
            repo=repo,
            findings=[
                f"local_head:{local.stdout.strip()!r} != {head!r}"
            ],
            stdout_tail=_tail(local.stdout),
            stderr_tail=_tail(local.stderr),
        )

    env = os.environ.copy()
    for name in FORBIDDEN_FIRST_STEP_ENV:
        env.pop(name, None)
    env.update(
        {
            "BUILDKITE_COMMIT": head,
            "BUILDKITE_BRANCH": "ONE_SHOT_PREFLIGHT",
            "BUILDKITE_BUILD_ID": "ONE_SHOT_PREFLIGHT",
            "BUILDKITE_BUILD_NUMBER": "ONE_SHOT_PREFLIGHT",
            "MULTIVERSE_DISPATCHER_REF": dispatcher_ref,
        }
    )

    with tempfile.TemporaryDirectory(prefix="multiverse-one-shot-preflight-") as td:
        temp = Path(td)
        archive_path = temp / "dispatcher.tar"
        runner_root = temp / "runner"
        runner_root.mkdir()

        archived = command_runner(
            [
                "git",
                "archive",
                "--format=tar",
                f"--output={archive_path}",
                dispatcher_ref,
                "automation/review_dispatcher_v1",
            ],
            cwd=str(root),
            text=True,
            capture_output=True,
        )
        if archived.returncode != 0:
            return _result(
                ready=False,
                classification="DISPATCHER_REF_ARCHIVE_FAILURE",
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                stdout_tail=_tail(archived.stdout),
                stderr_tail=_tail(archived.stderr),
            )

        try:
            _safe_extract_tar(archive_path, runner_root)
        except Exception as exc:
            return _result(
                ready=False,
                classification="DISPATCHER_REF_ARCHIVE_INVALID",
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                findings=[repr(exc)],
            )

        runner_pythonpath = str(runner_root)
        runner_env = dict(env)
        runner_env["PYTHONPATH"] = runner_pythonpath
        job_path = temp / "review_job.json"
        artifact_path = temp / "review_artifact.json"

        dispatch = command_runner(
            [
                sys.executable,
                str(
                    runner_root
                    / "automation/review_dispatcher_v1/dispatcher.py"
                ),
                "--lane",
                lane,
                "--repo",
                repo,
                "--head",
                head,
                "--output",
                str(job_path),
            ],
            cwd=str(root),
            env=runner_env,
            text=True,
            capture_output=True,
        )
        if dispatch.returncode != 0 or not job_path.exists():
            return _result(
                ready=False,
                classification=_failure_class(dispatch.stdout, dispatch.stderr),
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                stdout_tail=_tail(dispatch.stdout),
                stderr_tail=_tail(dispatch.stderr),
            )

        try:
            job = json.loads(job_path.read_text())
        except Exception as exc:
            return _result(
                ready=False,
                classification="DISPATCHER_JOB_INVALID_JSON",
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                findings=[repr(exc)],
            )

        binding_findings: list[str] = []
        if job.get("schema") != FIXED_JOB_SCHEMA:
            binding_findings.append(f"job_schema:{job.get('schema')!r}")
        if job.get("dispatcher_ref") != dispatcher_ref:
            binding_findings.append(
                f"dispatcher_ref:{job.get('dispatcher_ref')!r} != {dispatcher_ref!r}"
            )
        if job.get("head") != head:
            binding_findings.append(f"head:{job.get('head')!r} != {head!r}")
        if job.get("lane") != lane:
            binding_findings.append(f"lane:{job.get('lane')!r} != {lane!r}")
        if job.get("repo") != repo:
            binding_findings.append(f"repo:{job.get('repo')!r} != {repo!r}")
        if job.get("main") != dispatcher_ref:
            binding_findings.append(
                f"main:{job.get('main')!r} != dispatcher_ref:{dispatcher_ref!r}"
            )
        if binding_findings:
            return _result(
                ready=False,
                classification="DISPATCHER_JOB_BINDING_MISMATCH",
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                job=job,
                findings=binding_findings,
            )

        review = command_runner(
            [
                sys.executable,
                str(runner_root / "automation/review_dispatcher_v1/review.py"),
                "--job",
                str(job_path),
                "--output",
                str(artifact_path),
                "--repo-root",
                str(root),
            ],
            cwd=str(root),
            env=runner_env,
            text=True,
            capture_output=True,
        )

        artifact: dict[str, Any] | None = None
        artifact_error: str | None = None
        if artifact_path.exists():
            try:
                loaded = json.loads(artifact_path.read_text())
                if isinstance(loaded, dict):
                    encoded = json.dumps(loaded, sort_keys=True, separators=(",", ":"))
                    round_trip = json.loads(encoded)
                    if round_trip != loaded:
                        artifact_error = "ARTIFACT_JSON_ROUND_TRIP_MISMATCH"
                    else:
                        artifact = loaded
                else:
                    artifact_error = "ARTIFACT_NOT_OBJECT"
            except Exception as exc:
                artifact_error = repr(exc)

        if artifact_error is not None:
            return _result(
                ready=False,
                classification="REVIEW_ARTIFACT_SERIALIZATION_FAILURE",
                dispatcher_ref=dispatcher_ref,
                head=head,
                lane=lane,
                repo=repo,
                job=job,
                findings=[artifact_error],
                stdout_tail=_tail(review.stdout),
                stderr_tail=_tail(review.stderr),
            )

        ready, classification, findings = classify_review_outcome(
            returncode=review.returncode,
            artifact=artifact,
        )
        return _result(
            ready=ready,
            classification=classification,
            dispatcher_ref=dispatcher_ref,
            head=head,
            lane=lane,
            repo=repo,
            job=job,
            artifact=artifact,
            findings=findings,
            stdout_tail=_tail(review.stdout),
            stderr_tail=_tail(review.stderr),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dispatcher-ref", required=True)
    parser.add_argument("--lane", required=True, choices=("LAB", "AUDITOR"))
    parser.add_argument(
        "--repo", default="fufufu1116/multiverse-research"
    )
    parser.add_argument("--head", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    result = run_one_shot_preflight(
        dispatcher_ref=args.dispatcher_ref,
        lane=args.lane,
        repo=args.repo,
        head=args.head,
        repo_root=Path(args.repo_root),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
