# MULTIVERSE Real Infrastructure Preparation v1

Issue: #118

Owner preparation authority: Issue #117 comment `5540239175`.

## Scope

This directory defines a provider-neutral, deterministic preparation contract for the next remote PRE_PRODUCTION evidence phase.

Selected target class:

`REMOTE_PREPRODUCTION_SINGLE_HOST_NO_EFFECT_PLANNED_v1`

This is specification-only. It does not claim any remote infrastructure exists.

## Files

- `real_infrastructure_contract.py` — exact-type fail-closed preparation contract.
- `preparation_plan.py` — deterministic synthetic preparation plan.
- `test_real_infrastructure_contract.py` — adversarial contract tests.
- `test_preparation_plan.py` — plan/proof-ceiling tests.
- `PREPARATION_SELECTION.md` — target-class selection and authority boundary.
- `CANDIDATE_READINESS_v1.md` — readiness boundary for later specification review.
- `CANDIDATE_SEAL_v1.json` — durable preparation-scope seal.

## Default deny

The preparation contract requires exact `False` for:
- real network execution;
- live provider execution;
- external effects;
- spend;
- protected Keirin data;
- production credentials;
- production deployment;
- Runtime activation.

It also requires exact `False` for existence claims that would otherwise overstate the preparation phase:
- remote host provisioned;
- remote service deployed;
- remote state store provisioned;
- real credentials provisioned;
- network path verified.

## Test command

`python -m unittest discover -s automation/real_infrastructure_prep_v1 -p 'test_*.py' -v`

## Proof ceiling

`REMOTE_PREPRODUCTION_SPECIFICATION_ONLY`

Passing this preparation suite means the specification is internally coherent and fail-closed. It does not prove a remote host, service, state store, credentials, network path, production deployment, or Runtime activation readiness.

Runtime remains **OFF**.
