from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MODULES = (
    "automation.review_dispatcher_v1.dispatcher",
    "automation.review_dispatcher_v1.review",
    "automation.review_dispatcher_v1.publisher",
    "automation.review_dispatcher_v1.t2",
)


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError("BOOTSTRAP_COMMAND_FAILED:\n" + proc.stdout)
    return proc.stdout


def run_smoke(repo_root: Path, ref: str = "HEAD") -> None:
    with tempfile.TemporaryDirectory(prefix="mv-auditor-bootstrap-") as tmp:
        root = Path(tmp)
        archive = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "archive",
                ref,
                "automation/review_dispatcher_v1",
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        subprocess.run(
            ["tar", "-x", "-C", str(root)],
            input=archive.stdout,
            check=True,
        )

        dispatcher = root / "automation/review_dispatcher_v1/dispatcher.py"
        if not dispatcher.is_file():
            raise RuntimeError("DISPATCHER_ARCHIVE_MISSING")

        env = dict(os.environ)
        env["PYTHONPATH"] = str(root)

        for module in MODULES:
            _run(
                [sys.executable, "-c", f"import {module}"],
                cwd=repo_root,
                env=env,
            )

        output = _run(
            [sys.executable, str(dispatcher), "--help"],
            cwd=repo_root,
            env=env,
        )
        if "--lane" not in output or "--repo" not in output:
            raise RuntimeError("DISPATCHER_HELP_CONTRACT_MISSING")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ref", default="HEAD")
    args = parser.parse_args()
    run_smoke(Path(args.repo_root).resolve(), args.ref)
    print("AUDITOR_BOOTSTRAP_SMOKE_V2_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
