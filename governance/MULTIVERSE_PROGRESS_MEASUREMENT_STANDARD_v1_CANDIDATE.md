# MULTIVERSE Progress Measurement Standard v1 — CANDIDATE

Status: CANDIDATE. Prevents invented progress percentages.

## A. Current-work progress
Each mission defines weighted completion gates before reporting a percentage. Default only when mission has no stronger domain-specific scale:
- scope/current-state evidence fixed: 10
- design/plan complete: 15
- implementation/work product complete: 35
- automated/mechanical checks complete: 20
- required independent review complete: 20
Total: 100.

A blocked or failed gate does not earn its weight. If gates are not defined or evidence cannot be checked, report 算定保留.

## B. MULTIVERSE final-completion progress
Do not publish a numeric overall percentage until a canonical North-Star completion ledger is adopted.
The ledger must define major capability areas, weights, acceptance evidence, dependencies, governance gates, recovery tests and runtime maturity.
A single PR, chat, research lane or provider integration cannot stand in for overall MULTIVERSE completion.

## C. Evidence
Every reported percentage must be reproducible from canonical evidence and identify the measurement version. No mood-based or narrative-only percentages.

## D. Owner display
Use plain Japanese:
今取り掛かっている作業の進捗度：XX%（or 算定保留）
MULTIVERSE完成版までの進捗：XX%（or 算定保留）
