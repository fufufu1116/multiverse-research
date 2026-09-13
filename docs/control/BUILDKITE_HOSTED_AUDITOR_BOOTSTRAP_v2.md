# MULTIVERSE Independent Auditor — executable bootstrap v2

Status: repository-only candidate
Parent: Issue #450
Runtime: OFF

This successor preserves PR #444's explicit canonical-main ref repair, restores the proven Python bootstrap shape, and removes a second copy of the Buildkite Steps payload from prose.

## Single source of truth for external Steps

The complete candidate Steps payload is exactly:

`buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_HOSTED_v2.yml`

Do not reconstruct it from snippets and do not edit only one block. Any future Owner-authorized external Steps change must use the complete exact file contents after Fresh SHA verification.

The file contains all three required stages:
1. Independent Auditor dispatcher/review;
2. trusted result publisher;
3. T2.

This prevents the v1 failure mode where a partial replacement could silently drop downstream publisher/T2 stages.

## Error class repaired

Build #2314 failed before review execution with:

`ModuleNotFoundError: No module named 'automation'`

Fresh historical search also found the same signature on prior Auditor bootstrap Build #2015, recorded in Gate #399. The earlier repair proof used absolute `$PWD`-based PYTHONPATH in ordinary GitHub Actions, but did not emulate Buildkite YAML interpolation. The lesson was not generalized at that time.

Buildkite documents that runtime variables in pipeline YAML must escape `$` as `$$` or `\$`. Therefore v2 treats pipeline interpolation as a separate proof layer rather than assuming ordinary shell behavior is sufficient.

## v2 invariants

- canonical-main fetch/archive uses explicit `refs/remotes/origin/main`; no `FETCH_HEAD` dependency in any stage;
- all three Auditor stages remain present and on queue `independent-auditor`;
- runtime shell variables are escaped for Buildkite interpolation;
- Python entry points use inline `PYTHONPATH=.mv_dispatcher` rather than an interpolated `$PWD` export;
- dispatcher, publisher and T2 each have an import smoke before effectful execution;
- focused preflight rejects single-dollar runtime variables and incomplete three-stage payloads;
- isolated archive/import smoke actually runs the archived dispatcher `--help` before any external Build is considered.

## Mandatory pre-external proof

Before any new Owner-gated external Auditor attempt:
- full stored-YAML static preflight PASS;
- focused regression suite PASS;
- isolated `git archive -> extract -> import -> dispatcher --help` smoke PASS;
- normal candidate CI PASS;
- normal independent review sequence PASS;
- exact external Steps payload separately Owner-authorized;
- new one-shot Build separately Owner-authorized.

An external Build must be the last confirmation, not the first time the bootstrap is exercised.

This document grants no external Buildkite mutation, Build/Retry/rerun/reuse, merge/adoption, provider/spend/live effect, or Runtime authority.

`RUNTIME: OFF`
