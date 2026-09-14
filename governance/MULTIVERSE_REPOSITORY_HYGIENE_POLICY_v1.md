# MULTIVERSE Repository Hygiene / Information Lifecycle Policy v1

Status: CANDIDATE / REPOSITORY-ONLY / NON-AUTHORITY
Parent control: Issue #394
Runtime: OFF

## Purpose
Keep a growing MULTIVERSE repository recoverable by Fresh Read without erasing audit, experiment, Owner-decision, reproducibility, or recovery evidence.

This policy generalizes the existing Keirin `FILE_AND_COMMUNICATION_SIMPLIFICATION_POLICY_v1.md` pattern. It does not create a competing authority registry.

## Core rule
Physical age is never sufficient reason for deletion. Classify by lifecycle and authority semantics first.

## Lifecycle classes

### CURRENT_POINTER
Small, machine-readable locator for normal resume. At most one current pointer per declared scope. It points to exact canonical sources; it does not copy large history.

### ADOPTED_CANONICAL
Currently adopted code, policy, contract, registry, model, or active operational document on canonical main.

### EVIDENCE_IMMUTABLE
Owner decisions, adoption/integration receipts, independent Lab/Auditor evidence, experiment ledgers/results, failures, postmortems, preregistrations, provenance, recovery receipts, and other material audit evidence. Retain regardless of age unless a separately governed evidence migration proves integrity and replacement.

### ARCHIVE_OBSOLETE
Superseded implementation/docs/snapshots that are no longer current but remain useful for history, reproducibility, or recovery. They must be clearly indexed as superseded and must not be mistaken for CURRENT.

### TEMPORARY_GENERATED
Reproducible proof carriers, scratch exports, generated bundles, one-off transient CI helpers, caches, and temporary reports that are not referenced by durable evidence. They may become deletion candidates only after retention checks.

### PROTECTED_SEALED
Protected/holdout/regulated/sensitive lineage. Hygiene automation must never open, relocate, rewrite, or delete it merely for cleanup.

## Decision labels
Every reviewed path is assigned one of:
- KEEP_ACTIVE
- KEEP_EVIDENCE
- RETIRE_FROM_ACTIVE_VIEW
- CONSOLIDATION_CANDIDATE
- DELETION_CANDIDATE
- PROTECTED_NO_TOUCH
- UNKNOWN_FAIL_CLOSED

`DELETION_CANDIDATE` is not deletion authority.

## Current recovery surface rule
Normal Fresh Read should start from a tiny repository index and CURRENT pointers, not from filename archaeology. A CURRENT pointer must declare scope, status, canonical refs, supersedes/superseded_by if known, and last verified main SHA.

Historical files named CURRENT are not automatically current. Fresh GitHub authority wins.

## Evidence preservation rule
Never delete because a newer version exists when the older object is any of:
- formal review/request/result/receipt evidence;
- Owner decision or authority record;
- experiment result, failure, negative control, postmortem, or ledger;
- reproducibility input/manifest;
- recovery/bootstrap evidence;
- protected-data boundary metadata.

Prefer indexing/retiring from the active view over physical deletion.

## Retention defaults
These are classification defaults, not deletion authority:
- EVIDENCE_IMMUTABLE / PROTECTED_SEALED: indefinite.
- ADOPTED_CANONICAL: while adopted; then normally ARCHIVE_OBSOLETE or EVIDENCE_IMMUTABLE.
- superseded CURRENT snapshots: retain until indexed successor + recovery equivalence are verified; then RETIRE_FROM_ACTIVE_VIEW.
- TEMPORARY_GENERATED unreferenced proof/scratch: review after 30 days.
- generated bulky non-authoritative artifacts whose durable receipt/hash exists: review after 90 days.

Tracked-file deletion remains fail-closed and requires the applicable governance/Owner Gate until a separately adopted deletion authority exists.

## Naming / layout rules for new work
1. Stable live entrypoints use unversioned locator names only when their semantics are explicitly mutable pointers.
2. Immutable evidence uses dated/versioned names and is never called CURRENT unless it is a pointer.
3. Candidate/experimental objects include `candidate`, `draft`, `experiment`, `proof`, or an experiment ID in metadata/name.
4. Do not nest `.github/workflows` inside `.github/workflows`.
5. Proof workflows belong on proof branches when possible, not permanent main.
6. New version siblings require explicit predecessor/successor metadata or an index entry.
7. Do not create a new registry when an existing canonical registry can be extended safely.

## Repository index design
A future adopted `governance/MULTIVERSE_REPOSITORY_INDEX_v1.json` should be generated/validated from main and contain only pointers and classifications, not copied artifact bodies. Minimum sections:
- canonical_main_observed
- current_entrypoints by scope
- adopted_surfaces
- evidence_roots
- archive_roots
- protected_roots
- known_hygiene_findings
- generated_at / generator_version

It is a locator/index, not an authority replacement for Git history, issues, PRs, or review receipts.

## Automation rule
The hygiene audit is read-only by default. It may report:
- nested workflow trees;
- multiple CURRENT-like files in one scope;
- adjacent version siblings;
- candidate/draft/proof files on main;
- likely temporary outputs;
- exact-content duplicates where detectable;
- missing lifecycle metadata/index coverage.

It must not auto-delete, auto-move, auto-close issues, rewrite evidence, touch protected material, or infer adoption solely from filenames.

## Initial Fresh inventory findings (main e875d491853ab9a27158b617ff185d14ac804039)
- root mixes human/current entrypoints with historical/scientific surfaces (`MULTIVERSE_BOOTSTRAP.md`, `KEIRIN_NOW.md`, `START_HERE_MULTIVERSE_KEIRIN.md`, `nextgen`, `multiverse_vnext`, `v3`).
- `MULTIVERSE_BOOTSTRAP.md` still routes normal bootstrap to `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`, an accepted-foundation-era state rather than all later control/lane state.
- governance contains multiple version chains/current-state snapshots and lifecycle registries side-by-side; these are evidence/history but need active-vs-superseded indexing.
- automation contains sequential orchestrator generations v3/v4/v5/v6/v7 side-by-side; filenames alone do not provide lifecycle status.
- `v3/historical_all_market/` intentionally mixes active lineage code, notebooks, governance receipts, runtime receipts, and old version siblings; this is evidence-rich and must not be bulk-cleaned.
- `.github/workflows/.github/workflows/` exists and is a structural anomaly requiring provenance review before any removal.

## First migration sequence
1. adopt/validate classification and index semantics;
2. generate read-only audit reports;
3. mark current/adopted/evidence/archive status without moving files;
4. only then propose relocations/consolidations;
5. physical deletion last, separately authorized, with exact path list and recovery proof.

RUNTIME: OFF
