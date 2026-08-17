# Multiverse Recovery Protocol v1

If context is lost, device is replaced, the app is deleted, or the user says they no longer understand the state:

1. Do not execute anything first.
2. Read MULTIVERSE_STATE.json.
3. Read MULTIVERSE_ARTIFACT_REGISTRY.json.
4. Read MULTIVERSE_DECISION_LOG.md.
5. Verify active branch, HEAD, manifests and protected SHA-256 values.
6. Verify ECON_HOLDOUT1000 / PRICE / PAYOUT access state without opening sealed data.
7. Explain the reconstructed state in plain Japanese.
8. Only then continue.

Emergency phrase:
Multiverseを復旧して。GitHubのSTATE/RECOVERY/ARTIFACT_REGISTRY/DECISION_LOGと最新manifestから現在地を再構築して。Freeze/HOLDOUT状態を変更せず続行。

Rules:
- GitHub evidence is authoritative; chat memory is only a hint.
- Never Freeze without independent APPROVE.
- Never open real HOLDOUT/PRICE/PAYOUT merely to recover context.
- Search GitHub -> ChatGPT File Library -> Google Drive before asking the user to re-upload.
- No required research state may live only on an iPhone or in one chat.
