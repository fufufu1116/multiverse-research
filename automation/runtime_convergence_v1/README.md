# MULTIVERSE Runtime Convergence v1

This directory is a **repository-only convergence preparation surface** for Issue #133.

It does not activate Runtime and does not perform provider execution.

## What this Candidate materializes

The Candidate is based on canonical main
`a6f56facc80709f2e7b8218d927484d522bfa356`.

It materializes exact Git subtrees from already-adopted evidence lineages:

- Runtime Supervisor v1;
- deployment evidence v1;
- local PRE_PRODUCTION target evidence;
- real-infrastructure preparation;
- adopted single-Render no-effect evidence;
- multi-host preparation;
- adopted real two-worker Render no-effect evidence.

Each imported directory is bound by an exact source commit, source tree, subtree
SHA, adoption issue, and adoption comment in `CONVERGENCE_CONTRACT_v1.json`.

This is deliberate: evidence-only adoption did not merge those PRs into main.
The convergence Candidate therefore makes the already-adopted surfaces coexist in
one reviewable exact tree **without mutating canonical main** and without pretending
that later drift on an old PR is part of an earlier adoption.

## Current proof ceiling

`RUNTIME_CONVERGENCE_REPOSITORY_PREPARATION_ONLY`

The Candidate can prove repository-level compatibility and exact provenance. It
cannot prove production deployment, production credentials, live business effects,
protected Keirin data use, paid spend, HTTP/network-partition SLOs, multi-region
failover, Postgres HA, or Runtime activation.

## Runtime safety

Runtime is `OFF`.

The materialized Runtime Supervisor remains `SEALED_DRY_RUN` with its durable
kill switch engaged by default. Deployment and target capability maps remain
default-deny. No new Render drill, resource creation, environment-variable change,
secret operation, or provider action is part of this Candidate.

## Review path

The intended path is:

`Candidate freeze -> Independent Lab -> T1 -> Independent Auditor -> T2 -> separate Owner decision`

No review artifact can self-adopt this Candidate.


## 統合境界

ここはかなり重要です。

このCandidateは、採用済みの材料を **同じGit tree上に正確に並べて矛盾なく検査できる状態** まで進めますが、まだRuntime Supervisorの内部状態ストアをRender Postgresへ置き換えたわけではありません。

現在の明示的境界:

- Runtime control store: `LOCAL_SQLITE_SEALED`
- distributed fencing evidence store: `RENDER_POSTGRESQL`
- provider-effect adapter: disabled
- Runtime activation bridge: disabled
- canonical convergence merge: not completed
- activation integration: still required

したがって:

`PREPARATION_NOT_ACTIVATABLE`

です。

これは失敗ではなく、証拠採用と実際のRuntime起動を混同しないための安全境界です。
