# Render Remote PRE_PRODUCTION No-Effect Evidence v1

Issue: #122

Authority: Issue #121 comment `5549002692`.

This service is a bounded PRE_PRODUCTION evidence workload only.

## Runtime boundaries

- Runtime: OFF
- no production credentials
- no protected Keirin data
- no betting/trading/action provider
- no external business effect
- no outbound application API calls
- all HTTP POST operations rejected
- evidence startup mutations require exact environment authority token
  `AUTHORIZED_NO_EFFECT_EVIDENCE_V1`

## Evidence endpoints

- `GET /health`
- `GET /ready`
- `GET /evidence`

## Remote state drill

When exact no-effect evidence authority and a PRE_PRODUCTION database are bound, startup performs:

- boot counter persistence
- application-level backup snapshot digest
- bounded corruption simulation
- restore and digest comparison
- single-host lease owner/fence transition
- idempotency duplicate control

The service never interprets this as production readiness.

## Proof ceiling

`REMOTE_PREPRODUCTION_SINGLE_RENDER_NO_EFFECT_EVIDENCE_ONLY`

Runtime remains OFF.
