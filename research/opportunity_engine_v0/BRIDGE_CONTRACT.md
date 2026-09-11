# Opportunity Engine -> MULTIVERSE Bridge Contract v0

Status: RESEARCH PROTOTYPE ONLY  
Runtime: OFF

## Purpose

Connect Opportunity Engine research output to the existing canonical MULTIVERSE research/review contract without creating a second governance system.

The bridge is intentionally thin:

`Opportunity case -> frozen hash-bound packet -> MULTIVERSE_RESEARCH_TASK_v2 -> existing MULTIVERSE review machinery`

The bridge does not execute a provider, choose a canonical result, grant adoption authority, mutate main, spend money, publish, or activate Runtime.

## Why reuse the existing task contract

Canonical MULTIVERSE already defines research task constraints, evidence manifests, non-authority flags, bounded roles and fail-closed validation. Opportunity Engine should consume that contract rather than invent parallel Core/Vault/Lab/Auditor semantics.

`multiverse_bridge.py` therefore imports `NONAUTHORITY_KEYS` and `validate_task` from `automation.multimodel_research_v1.model`.

## Frozen case identity

Each bridge packet contains:
- the extracted Opportunity Engine case;
- a SHA-256 over canonical JSON of that extracted case;
- a case reference locating the source snapshot/case;
- a `MULTIVERSE_RESEARCH_TASK_v2` whose source reference and evidence manifest carry the same case digest;
- a packet-level SHA-256 protecting the outer bridge packet.

The case digest is the digest of the normalized extracted case object, not a Git blob SHA of an entire batch file. A fragment-style case reference may therefore point at one case inside a larger research batch while the digest binds the extracted case payload itself.

If the opportunity case, source hash, case reference, authority flags or outer packet are rewritten after freeze, validation must fail.

## Default independent challenge

The default bridge requests three bounded challenge roles:
- `competitor_challenge`;
- `economics_challenge`;
- `execution_risk_challenge`.

The task objective explicitly tells reviewers not to accept the Opportunity Engine provisional verdict as truth. It asks them to attack competitor coverage, general-AI/incumbent substitution, payer clarity, economics, demand lifetime, leverage assumptions, owner burden, copy exposure, legal/safety risk, kill conditions and simpler existing-service alternatives.

## Authority boundary

Every bridge and task non-authority flag remains `false`. The bridge cannot authorize:
- adoption or merge;
- canonical/main mutation;
- workflow rerun;
- Runtime activation;
- provider/live-business effect;
- production;
- protected-data access;
- spending.

A later governed MULTIVERSE path may independently authorize some action. The bridge itself never does.

## Network boundary

v0 bridge review tasks use `network_access = NONE` because they review a frozen evidence-bearing opportunity snapshot. Fresh evidence gathering remains an upstream research action and must be frozen into a new case before another review packet is created. This prevents a reviewer from silently changing the evidence universe while judging a frozen candidate.

## First concrete bridge specimen

`cases/review_packet_office2021_eos_jp_v1.json` is the first research-only specimen. It transforms the already-recorded Office 2021 end-of-support case into a hash-bound MULTIVERSE review task without running any external provider or creating a live effect.

## Next research step

Add a bounded adapter for MULTIVERSE research results back into Opportunity Engine as advisory evidence. That return adapter must preserve model identity, task identity, evidence refs, uncertainty and non-authority. It must not translate a model finding directly into execution or adoption.
