from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = (ROOT / "candidate/security_v3_3").resolve()
MAX_FILES = 5
MAX_BYTES = 120 * 1024
TOP_KEYS = {"schema_version","attempt","base_candidate_sha256","changes","reason","expected_fixed_tests"}
CHANGE_KEYS = {"path","operation","content"}


def candidate_sha() -> str:
    h = hashlib.sha256(); base = ROOT / "candidate/security_v3_3"
    if not base.exists(): return hashlib.sha256(b"empty").hexdigest()
    for p in sorted(base.rglob("*")):
        if p.is_symlink(): raise PermissionError("FAIL_CLOSED: candidate symlink detected")
        if p.is_file(): h.update(p.relative_to(base).as_posix().encode()); h.update(b"\0"); h.update(p.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def apply_patch(payload: str) -> dict:
    try: obj = json.loads(payload)
    except Exception as e: raise PermissionError(f"FAIL_CLOSED: invalid JSON: {e}")
    if not isinstance(obj, dict) or set(obj) != TOP_KEYS: raise PermissionError("FAIL_CLOSED: top-level schema mismatch")
    if obj["schema_version"] != "mv33-patch-v1": raise PermissionError("FAIL_CLOSED: schema_version mismatch")
    if not isinstance(obj["attempt"], int) or obj["attempt"] < 1: raise PermissionError("FAIL_CLOSED: invalid attempt")
    before = candidate_sha()
    if obj["base_candidate_sha256"] != before: raise PermissionError("FAIL_CLOSED: base_candidate_sha256 mismatch")
    changes = obj["changes"]
    if not isinstance(changes, list) or not changes or len(changes) > MAX_FILES: raise PermissionError("FAIL_CLOSED: invalid changes count")
    total = 0
    for c in changes:
        if not isinstance(c, dict) or set(c) != CHANGE_KEYS: raise PermissionError("FAIL_CLOSED: change schema mismatch")
        rel = c["path"]; op = c["operation"]; content = c["content"]
        if not all(isinstance(x, str) for x in [rel,op,content]): raise PermissionError("FAIL_CLOSED: non-string change field")
        pp = Path(rel)
        if pp.is_absolute() or ".." in pp.parts or not rel.startswith("candidate/security_v3_3/"): raise PermissionError("FAIL_CLOSED: path escape")
        total += len(content.encode("utf-8"))
        if total > MAX_BYTES: raise PermissionError("FAIL_CLOSED: patch too large")
        raw = ROOT / pp
        cur = ROOT
        for part in pp.parts[:-1]:
            cur = cur / part
            if cur.exists() and cur.is_symlink(): raise PermissionError("FAIL_CLOSED: parent symlink")
        target = raw.resolve(strict=False)
        try: target.relative_to(ALLOWED)
        except ValueError: raise PermissionError("FAIL_CLOSED: outside allowed root")
        if target.exists() and target.is_symlink(): raise PermissionError("FAIL_CLOSED: target symlink")
        if op == "create" and target.exists(): raise PermissionError("FAIL_CLOSED: create-existing")
        if op == "replace" and not target.is_file(): raise PermissionError("FAIL_CLOSED: replace-missing")
        if op not in {"create","replace"}: raise PermissionError("FAIL_CLOSED: forbidden operation")
        target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding="utf-8")
    return {"before_sha256": before, "after_sha256": candidate_sha(), "changed_files": [c["path"] for c in changes]}
