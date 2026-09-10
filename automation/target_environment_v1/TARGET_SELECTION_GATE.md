# Target Selection Gate

Status: `OWNER_OR_TARGET_AUTHORITY_REQUIRED_BEFORE_BOUND_CANDIDATE`

The generic construction harness is complete enough to enforce evidence shape and default-deny authority, but a **bound target-environment Candidate must not be created from invented infrastructure values**.

Before Candidate creation, an authorized decision must bind:

1. exact target platform/provider;
2. exact environment class (`PRE_PRODUCTION` or `PRODUCTION_SHADOW_NO_EFFECT`);
3. exact target identifier/name;
4. whether the target is single-host by design or expected to demonstrate multi-host failover;
5. approved non-production credential path for the target evidence drills.

The following remain prohibited at this gate: Runtime activation, production credentials, live external effects, spend, protected Keirin data, main/ruleset mutation, and workflow dispatch/rerun authority.

Until these values are bound, `target_manifest.template.json` remains a template only and cannot constitute PASS evidence.
