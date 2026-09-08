# MULTIVERSE Combined Control-Plane Fault Replay Harness v1

Status: repository-only Research Lane B closure Candidate for Issue #241 / parent #239.

RUNTIME: OFF.

## Purpose

Exercise the interaction of the frozen hardening ideas in one deterministic in-memory replay before any final adoption-time combined proof.

Covered sequence:
1. same-generation request collision;
2. legitimate supersession from the canonical winner;
3. stale old job rejection after supersession;
4. concurrent trusted PASS publication plus untrusted noise;
5. canonical result receipt recovery after simulated receipt loss;
6. concurrent trusted T2 publication plus untrusted noise;
7. canonical T2 receipt recovery;
8. loser-derived successor / duplicate request ID / missing trusted evidence negative controls.

## Expected convergence

For the reference interleaving:
- canonical request comments: `[10, 20]`;
- canonical result comment: `100`;
- canonical T2 comment: `200`;
- stale request job rejected;
- result receipt recovered from canonical durable result;
- T2 receipt recovered from canonical durable T2;
- final verdict: `PASS`.

## Proof boundary

This is a pre-adoption repository-only simulation. It does not replace Independent Lab/Auditor review, actual integration of the frozen Candidates, or the final post-adoption combined replay required by the Lane B completion matrix. A PASS here is preparation evidence only and must not flip `combined_fault_replay` to `ADOPTED_PROVEN`.

Proof ceiling:
`COMBINED_CONTROL_PLANE_FAULT_REPLAY_HARNESS_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
