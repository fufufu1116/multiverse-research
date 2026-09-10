# Placeholder Non-Evidence Rule

Values in `target_manifest.template.json` are scaffolding only.

The following must fail governance review if left unbound: target/provider identity, artifact digests, rollback digests, credential-path evidence, provider/effect evidence, state-store/backup/recovery evidence, observability evidence, kill-switch evidence, and rollback execution evidence.

A syntactically valid `EVIDENCE_REF:` string does not prove the referenced action happened. Independent Lab/Auditor must verify every bound reference against durable target-environment evidence before any PASS.
