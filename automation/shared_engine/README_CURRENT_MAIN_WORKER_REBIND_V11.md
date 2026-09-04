# AUTOMATION SHARED ENGINE CURRENT-MAIN WORKER REBIND v11

This Candidate is the smallest bridge after independently closed PR #97 v10. It does **not** add a provider, network path, deployed daemon, task-creation authority, production adoption, or Runtime.

## Why this exists

Fresh canonical main is `a6f56facc80709f2e7b8218d927484d522bfa356`, produced by merging the independently reviewed Shared Engine PR #91. Its exact Git tree is `2c957c4ad8a553b3a0e7122ebcdb22e75398afaf`, which is identical to reviewed PR #91 tree `2c957c4ad8a553b3a0e7122ebcdb22e75398afaf`. Git comparison from reviewed PR #91 head `61f4e330fd5b1945dbfbceb223cbc71d205860f2` to this main reports no file delta.

PR #96 v9 and PR #97 v10 were independently reviewed on the stacked candidate lineage, not on canonical main. v11 therefore imports only the functional v9/v10 implementation and adversarial test files **byte-for-byte** onto a new branch based on Fresh canonical main, then reruns inherited Shared Engine tests, v9 tests, v10 adversarial tests, and a v11 mechanical gate.

## Exact-source rule

The six functional v9/v10 files are pinned by Git blob identity in `CURRENT_MAIN_WORKER_REBIND_V11.json`. Any byte change to those files is a new semantic Candidate and invalidates this rebind proof.

No inherited PR #91 file is modified. In particular, `canonical_v7_binding.py` remains unchanged and still carries the reviewed PR #88 v7 contract-main identity `040d37f0a4e426cf2e119706484c90cbb48f0e56`.

That historical v7 contract-main identity and the repository's Fresh canonical main are deliberately treated as **different facts**. v11 proves only that the already-reviewed worker layers can be hosted on the current-main tree whose Shared Engine content is byte-identical to reviewed PR #91. It does **not** semantically rebind the PR #88 provider contract to the new main SHA.

## Safety boundary

The worker remains consume-only. PR91 SQLite remains sole workflow/task-state authority. v10 broker/client remain distinct local OS processes using strict local AF_UNIX JSON `PING` / `STEP` / `STOP`. Durable bounded non-evicting replay denial remains private transport denial state, not workflow authority.

The Candidate has no live-provider, provider-network, external-effect, spend, secret/credential, main/ruleset/production mutation, merge/adoption, protected-Keirin-data, workflow-dispatch/rerun, or Runtime authority.

## Proof ceiling

A PASS can establish only **current-main host compatibility** for the exact already-reviewed v9/v10 functional bytes on a tree byte-identical to reviewed PR #91, plus rerun regression evidence.

It does not prove a semantic rebind of `canonical_v7_binding.CANONICAL_MAIN`, authenticated external worker/provider/reviewer identity, malicious same-OS-user/root protection, replay reset/rotation lifecycle, remote-provider exactly-once, distributed/network lease safety, deployed always-on daemon/scheduler, production portability, adoption readiness, or Runtime.
