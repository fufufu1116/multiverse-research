# Multiverse Keirin — File / Communication Simplification Policy v1

Status: OPERATIONAL GOVERNANCE
Date: 2026-08-19 JST

## Goal

Research speed must increase without making the Owner carry technical vocabulary, file archaeology, or handoff reconstruction burden.

## User-facing rule

The Owner-facing default status file is:

`KEIRIN_NOW.md`

It must answer only:
1. what is being done now;
2. what was learned;
3. what happens next;
4. what the Owner needs to do.

Technical terms must either be avoided or immediately translated into ordinary Japanese.

## Repository visibility rule

Do not physically delete or rewrite immutable historical governance evidence merely to make the repository look cleaner.

Instead use three logical entrypoints:

### CURRENT
- `KEIRIN_NOW.md` — Owner dashboard
- `START_HERE_MULTIVERSE_KEIRIN.md` — automatic handoff/bootstrap
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json` — machine/canonical state

### CODE
- `v3/historical_all_market/new_lineage/` — active new-lineage implementation

### ARCHIVE / EVIDENCE
- `v3/historical_all_market/governance/` — preregistrations, audits, receipts, lessons, old checkpoints
- Drive — large historical artifacts

The Owner should not need to browse ARCHIVE/EVIDENCE during normal work.

## New file budget

Before creating a new governance file, No.3 asks internally:

1. Does this change scientific state, Freeze, provenance, audit result, or protected boundary?
2. Is it an immutable receipt that must be separately preserved?
3. Can the information instead be appended to an existing active design/current-state file?

If 1–2 are both no, prefer updating an existing file.

For active implementation, prefer a small number of cohesive modules over many one-function files.

## Naming rule

Owner-facing names: short and plain.
Internal scientific names may remain exact/technical.

Do not expose long SHA lists in ordinary progress reports unless a verification issue is material.

## Progress-report rule

Default report format:

**いま何をしてる**
plain-language sentence.

**分かったこと**
only material result; distinguish simulation from real evidence.

**次**
next concrete action.

**主がやること**
usually `なし`.

Avoid an acronym pile. If a term such as NLL, PL, CV, calibration, residual, provenance, or joint distribution is necessary, translate it once in parentheses.

## Speed rule

Do not block safe, source-independent engineering on data acquisition when synthetic fixtures can test plumbing/invariants.
Do not confuse this with predictive validation: synthetic evidence never replaces real-world validation.

Parallelize safe workstreams:
- world/simulator engineering;
- prediction architecture implementation;
- probability consistency tests;
- personal/public data-route audit;
- independent design audit preparation.

Only protected data/validation gates remain sequential.

## Handoff rule

At a new chat, load `KEIRIN_NOW.md` first for human state, then `CURRENT_STATE_KEIRIN.json` for exact machine state, then verify required artifacts.

END
