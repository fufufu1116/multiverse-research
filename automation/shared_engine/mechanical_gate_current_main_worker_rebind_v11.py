from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "automation/shared_engine/CURRENT_MAIN_WORKER_REBIND_V11.json"
EXPECTED_BRANCH = "agent/automation-shared-engine-current-main-worker-rebind-v11-20260904-v1"
EXPECTED_BASE_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
EXPECTED_SHARED_TREE = "2c957c4ad8a553b3a0e7122ebcdb22e75398afaf"
EXPECTED_PR91 = "61f4e330fd5b1945dbfbceb223cbc71d205860f2"
EXPECTED_V9 = "32b13303d888214215dd9a87cb6eef180bb52d69"
EXPECTED_V10 = "a4a845158bc03a0dbbc95cebd581b3334e1325b2"
EXPECTED_V7 = "4a72ef46116043094c7a8e494404956925a5b3bf"
EXPECTED_V7_CONTRACT_MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
EXPECTED_V10_CLOSURE = 5536530060
EXPECTED_PATHS = {
    ".github/workflows/multiverse-automation-shared-engine-current-main-worker-rebind-v11-prelab.yml",
    "automation/shared_engine/CURRENT_MAIN_WORKER_REBIND_V11.json",
    "automation/shared_engine/README_CURRENT_MAIN_WORKER_REBIND_V11.md",
    "automation/shared_engine/local_persistent_worker_v9.py",
    "automation/shared_engine/mechanical_gate_current_main_worker_rebind_v11.py",
    "automation/shared_engine/process_isolated_worker_broker_v10.py",
    "automation/shared_engine/process_isolated_worker_v10.py",
    "automation/shared_engine/tests/test_current_main_worker_rebind_v11.py",
    "automation/shared_engine/tests/test_local_persistent_worker_v9.py",
    "automation/shared_engine/tests/test_local_persistent_worker_v9_integration.py",
    "automation/shared_engine/tests/v10_test_process_isolated_worker.py",
}
EXPECTED_BLOBS = {
    "automation/shared_engine/local_persistent_worker_v9.py": "6056c50759147bd3a306bb6f71d54bb354ab7b60",
    "automation/shared_engine/tests/test_local_persistent_worker_v9.py": "9185be3271f5e0b6a631cfce2830a7bceafea2cc",
    "automation/shared_engine/tests/test_local_persistent_worker_v9_integration.py": "a256521162a46353519c0233a360c43fd48e09e6",
    "automation/shared_engine/process_isolated_worker_broker_v10.py": "54991d33e9ea8e9126fa51285483fa557799f72d",
    "automation/shared_engine/process_isolated_worker_v10.py": "9d65c61cbaf537064f95fc5489753664693974d0",
    "automation/shared_engine/tests/v10_test_process_isolated_worker.py": "134a1ccc40038a089cf58e69f4cb2f90efdc7fc7",
}

def require(ok: bool, code: str) -> None:
    if not ok:
        raise SystemExit(code)

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def main() -> None:
    d = json.loads(MANIFEST.read_text())
    require(d["branch"] == EXPECTED_BRANCH, "V11_BRANCH_BINDING")
    require(d["base_canonical_main"] == EXPECTED_BASE_MAIN, "V11_BASE_MAIN_BINDING")
    require(d["base_canonical_main_tree"] == EXPECTED_SHARED_TREE, "V11_BASE_TREE_BINDING")
    require(d["reviewed_pr91_head"] == EXPECTED_PR91, "V11_PR91_BINDING")
    require(d["reviewed_pr91_tree"] == EXPECTED_SHARED_TREE, "V11_PR91_TREE_BINDING")
    require(d["reviewed_v9_head"] == EXPECTED_V9, "V11_V9_BINDING")
    require(d["reviewed_v10_head"] == EXPECTED_V10, "V11_V10_BINDING")
    require(d["reviewed_v10_closure_comment"] == EXPECTED_V10_CLOSURE, "V11_V10_CLOSURE_BINDING")
    require(d["inherited_v7_head"] == EXPECTED_V7, "V11_V7_BINDING")
    require(d["inherited_v7_contract_main"] == EXPECTED_V7_CONTRACT_MAIN, "V11_V7_CONTRACT_MAIN_BINDING")
    require(git("rev-parse", f"{EXPECTED_BASE_MAIN}^{{tree}}") == EXPECTED_SHARED_TREE, "V11_BASE_MAIN_TREE_DRIFT")
    require(git("rev-parse", f"{EXPECTED_PR91}^{{tree}}") == EXPECTED_SHARED_TREE, "V11_PR91_TREE_DRIFT")
    changed = git("diff", "--name-only", EXPECTED_BASE_MAIN, "HEAD").splitlines()
    require(set(changed) == EXPECTED_PATHS and len(changed) == len(EXPECTED_PATHS), "V11_EXACT_PATH_SCOPE")
    status = git("diff", "--name-status", EXPECTED_BASE_MAIN, "HEAD").splitlines()
    require(all(line.startswith("A\t") for line in status), "V11_NEW_PATHS_ONLY")
    require(d["imported_exact_git_blobs"] == EXPECTED_BLOBS, "V11_MANIFEST_BLOB_BINDING")
    for rel, expected in EXPECTED_BLOBS.items():
        require(git_blob_sha(ROOT / rel) == expected, f"V11_IMPORTED_BLOB_DRIFT:{rel}")
    canonical = (ROOT / "automation/shared_engine/canonical_v7_binding.py").read_text()
    require(f'V7_HEAD="{EXPECTED_V7}"' in canonical, "V11_INHERITED_V7_HEAD_DRIFT")
    require(f'CANONICAL_MAIN="{EXPECTED_V7_CONTRACT_MAIN}"' in canonical, "V11_INHERITED_V7_MAIN_DRIFT")
    broker = (ROOT / "automation/shared_engine/process_isolated_worker_broker_v10.py").read_text()
    client = (ROOT / "automation/shared_engine/process_isolated_worker_v10.py").read_text()
    worker = (ROOT / "automation/shared_engine/local_persistent_worker_v9.py").read_text()
    combined = "\n".join((broker, client, worker))
    for forbidden in ("AF_INET", "AF_INET6", "requests.", "httpx.", "urllib.request", "subprocess.Popen", "create_task(", ".submit("):
        require(forbidden not in combined, f"V11_FORBIDDEN_SURFACE:{forbidden}")
    require("AF_UNIX" in broker and "AF_UNIX" in client, "V11_LOCAL_IPC_REQUIRED")
    a = d["architecture"]
    require(a["current_main_tree_equals_reviewed_pr91_tree"] is True, "V11_TREE_EQ_REQUIRED")
    require(a["v9_v10_functional_sources_imported_byte_for_byte"] is True, "V11_BYTE_IDENTITY_REQUIRED")
    require(a["inherited_pr91_files_modified"] is False, "V11_PR91_MUTATION_DENIED")
    require(a["inherited_v7_contract_rebound"] is False, "V11_V7_REBIND_DENIED")
    require(a["workflow_authority_remains_pr91_sqlite"] is True, "V11_SOLE_WORKFLOW_AUTHORITY")
    for key in ("live_provider", "network_provider", "external_effect", "spend", "secret_credential", "runtime"):
        require(a[key] is False, f"V11_AUTHORITY_FALSE:{key}")
    print("V11_MECHANICAL_GATE=PASS")
    print(f"V11_BASE_CANONICAL_MAIN={EXPECTED_BASE_MAIN}")
    print(f"V11_SHARED_ENGINE_TREE={EXPECTED_SHARED_TREE}")
    print(f"V11_IMPORTED_FUNCTIONAL_BLOBS={len(EXPECTED_BLOBS)}")
    print("V11_INHERITED_V7_CONTRACT_REBOUND=false")
    print("V11_RUNTIME=OFF")

if __name__ == "__main__":
    main()
