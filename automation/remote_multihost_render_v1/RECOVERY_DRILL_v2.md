# Remote Multi-Host Recovery Drill v2

The first real drill is preserved as failed evidence under Issue #130 diagnosis `5554083946`.

## Failure

Worker B started too early and its 240-second wait for `A_ACQUIRED` expired before worker A was manually deployed.

Observed first-run state:

- phase `A_ACQUIRED`
- fence token `1`
- operation count `1`
- worker-B fatal event `WAIT_TIMEOUT:phase_A_ACQUIRED`
- no valid token-2 or token-3 proof

No PASS is claimed from that run.

## Repair

The repaired workload uses a clean database drill identity:

`remote-multihost-render-v2-20260906`

The durable control-plane binding environment value remains:

`remote-multihost-render-v1-20260906`

This distinction preserves the exact Owner-authorized resource binding while isolating a new shared-state evidence namespace.

The orchestration wait is increased from 240 seconds to 900 seconds so normal manual deployment skew does not kill the waiting worker.

## Required clean v2 sequence

1. deploy worker B on the repaired commit;
2. deploy worker A on the same repaired commit within 15 minutes;
3. verify token 1 -> token 2, stale-owner, stale-fence, split-brain and cross-worker idempotency evidence;
4. manually redeploy worker A once more;
5. verify token 3, operation count 1 and phase COMPLETE;
6. collect exact provider logs/metrics and durable evidence;
7. only then create/seal the Candidate.

Runtime remains **OFF**.
