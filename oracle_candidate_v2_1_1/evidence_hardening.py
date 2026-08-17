from __future__ import annotations

import json
import multiprocessing as mp
import os
import time
from datetime import datetime, timezone
from pathlib import Path

def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")

def append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

def worker(path, key, audit_path, barrier, q, trace_path, worker_id):
    from candidate.security_v3_3 import api as m
    pid = os.getpid()
    append_jsonl(Path(trace_path), {"event":"PROCESS_START","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    gate = m.AuditedHoldoutGate(Path(path), key, Path(audit_path))
    append_jsonl(Path(trace_path), {"event":"BARRIER_READY","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    barrier.wait(timeout=10)
    append_jsonl(Path(trace_path), {"event":"BARRIER_RELEASED","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    append_jsonl(Path(trace_path), {"event":"OPEN_ATTEMPT_START","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    try:
        payload = gate.open_once(key)
        outcome = {"kind":"success","payload_hex":payload.hex()}
    except Exception as e:
        outcome = {"kind":"rejected","error_type":type(e).__name__,"error":str(e)}
    append_jsonl(Path(trace_path), {"event":"OPEN_ATTEMPT_END","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns(), **outcome})
    q.put((worker_id, pid, outcome))
    append_jsonl(Path(trace_path), {"event":"PROCESS_EXIT","worker":worker_id,"pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns(),"expected_exit_code":0})

def restart_worker(path, key, audit_path, q, trace_path):
    from candidate.security_v3_3 import api as m
    pid = os.getpid()
    append_jsonl(Path(trace_path), {"event":"RESTART_PROCESS_START","pid":pid,"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    gate = m.AuditedHoldoutGate(Path(path), key, Path(audit_path))
    state = gate.state()
    rows = [json.loads(x) for x in Path(audit_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    result = {"pid":pid,"state":state,"open_audit_count":sum(1 for r in rows if r.get("event")=="OPEN")}
    append_jsonl(Path(trace_path), {"event":"RESTART_STATE_READ","ts":iso_now(),"monotonic_ns":time.monotonic_ns(), **result})
    q.put(result)

def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main():
    root = Path(os.environ.get("MV33_REPO_ROOT", Path.cwd())).resolve()
    out = root / os.environ.get("EVIDENCE_HARDENING_DIR", "autopilot_v2_1_1_evidence")
    out.mkdir(parents=True, exist_ok=True)

    from candidate.security_v3_3 import api as m

    state_path = out / "holdout_state.json"
    audit_path = out / "holdout_audit.jsonl"
    trace_path = out / "concurrency_trace.jsonl"
    for p in (state_path, audit_path, trace_path):
        if p.exists():
            p.unlink()

    key = b"k" * 32
    gate = m.AuditedHoldoutGate(state_path, key, audit_path)
    gate.initialize(b"synthetic-payload")
    dump(out / "state_pre.json", gate.state())

    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(3)
    q = ctx.Queue()
    procs = [
        ctx.Process(target=worker, args=(str(state_path), key, str(audit_path), barrier, q, str(trace_path), f"W{i+1}"))
        for i in range(2)
    ]
    for p in procs:
        p.start()

    append_jsonl(trace_path, {"event":"PARENT_BARRIER_READY","pid":os.getpid(),"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})
    barrier.wait(timeout=10)
    append_jsonl(trace_path, {"event":"SIMULTANEOUS_RELEASE","pid":os.getpid(),"ts":iso_now(),"monotonic_ns":time.monotonic_ns()})

    for p in procs:
        p.join(15)
        if p.is_alive():
            p.terminate()
            raise SystemExit("FAIL_CLOSED: deadlock/process timeout")
        if p.exitcode != 0:
            raise SystemExit(f"FAIL_CLOSED: worker exitcode={p.exitcode}")

    results = [q.get(timeout=3) for _ in range(2)]
    success = sum(1 for _,_,o in results if o["kind"]=="success")
    rejected = sum(1 for _,_,o in results if o["kind"]=="rejected")

    post_gate = m.AuditedHoldoutGate(state_path, key, audit_path)
    post_state = post_gate.state()
    rows = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    post = {"state":post_state,"open_audit_count":sum(1 for r in rows if r.get("event")=="OPEN"),"success":success,"rejected":rejected,"workers":results}
    dump(out / "state_post.json", post)

    rq = ctx.Queue()
    rp = ctx.Process(target=restart_worker, args=(str(state_path), key, str(audit_path), rq, str(trace_path)))
    rp.start()
    rp.join(15)
    if rp.is_alive():
        rp.terminate()
        raise SystemExit("FAIL_CLOSED: restart process timeout")
    if rp.exitcode != 0:
        raise SystemExit(f"FAIL_CLOSED: restart exitcode={rp.exitcode}")
    restart = rq.get(timeout=3)
    dump(out / "state_restart.json", restart)

    required = (
        success == 1 and rejected == 1 and
        post_state.get("open_count") == 1 and post_state.get("nonce") == 2 and
        post["open_audit_count"] == 1 and
        restart["state"].get("open_count") == 1 and restart["state"].get("nonce") == 2 and
        restart["open_audit_count"] == 1
    )
    receipt = {
        "status":"PASS" if required else "FAIL_CLOSED",
        "success":success,"rejected":rejected,
        "post_state":post_state,
        "post_open_audit_count":post["open_audit_count"],
        "restart":restart,
        "deadlock_free":True,
        "freeze":False,
        "security_audit_passed":False,
        "synthetic_only":True,
    }
    dump(out / "EVIDENCE_HARDENING_RECEIPT.json", receipt)
    if not required:
        raise SystemExit("FAIL_CLOSED: evidence hardening invariant failed")
    print("ORACLE_V2_1_1_EVIDENCE_PASS")

if __name__ == "__main__":
    main()
