# Opportunity Engine — Autonomous Continuation Doctrine

Status: RESEARCH PROTOTYPE ONLY  
Runtime: OFF

## Core rule

Do not interrupt the Owner merely because one possible next step is gated.

Continue all useful, reversible, repository-only research that remains within existing authority. Defer gated actions while other safe research actions are available. Ask the Owner only when the next materially useful step truly requires Owner authority or Owner-only information.

## Continue without Owner

Examples include:
- research-branch code, tests, doctrines and fixtures;
- reversible refactors and validation improvements;
- competitor/substitute/AI-risk modeling using already authorized evidence sources;
- local simulation, scoring, forecasting and retrospective logic;
- privacy hardening, deduplication and evidence provenance work;
- research packet preparation that creates no live external effect;
- documentation and handoff strengthening;
- analysis of existing repository evidence;
- choosing another continuable research task when a different task is Owner-gated.

## Real Owner Gates

Stop and ask for one exact bounded action only when the next useful step requires one or more of:
- canonical-main mutation, adoption or merge authority;
- changes to fixed Lab/Auditor steps or governed review infrastructure;
- live provider/network calls not already authorized;
- credentials or secrets;
- money/spend/purchase/ad enrollment/paid provider use;
- publication, posting, outreach or external contact;
- live customer/business effect;
- Runtime activation;
- Owner-only facts or decisions that cannot safely be inferred from repository evidence;
- other explicitly governed authority boundaries.

## Fail-closed holds

Do not continue through:
- sensitive-owner-data exposure or destructive handling risk;
- ambiguous authority boundaries;
- unclassified non-reversible actions.

A fail-closed hold is not permission to ask a vague question. First search for another useful reversible research task. Ask the Owner only if no such task remains and the blocked action is materially necessary.

## Owner request format

When an Owner Gate is finally reached:
1. state exactly what has been completed;
2. state exactly why no useful reversible research step remains before the gate;
3. request one bounded authorization/action;
4. do not bundle unrelated permissions;
5. do not imply that a ready research posture is live authority.

## No background claim

This doctrine governs how work is selected during an active session or authorized execution turn. It does not claim background/asynchronous execution when no tool run is active.

See `owner_gate.py` and `test_owner_gate.py`.
