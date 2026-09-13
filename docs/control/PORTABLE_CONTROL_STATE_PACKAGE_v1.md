# Portable Control-State Package v1

Parent: Issue #432
Status: repository-only design candidate
Runtime: OFF

## Goal
Make MULTIVERSE recoverable without relying on ChatGPT chat state or one hosting/provider service.

## Package manifest
A portable package is a deterministic directory/archive with these non-secret components:

- `manifest.json` — schema version, package id, generated_at, source canonical backend/revision, integrity algorithm.
- `current_state.json` — current objectives, active lanes, blockers, next safe actions.
- `owner_command.json` — normalized `MULTIVERSE_OWNER_COMMAND_v1` projection.
- `fixed_rules.json` — durable Owner/control rules and supersession links.
- `decision_ledger.jsonl` — append-only material decisions/gates/adoptions/supersessions.
- `artifact_index.json` — content hashes plus external/local artifact locators; no embedded secrets.
- `provider_requirements.json` — capability requirements, not remembered provider names as authority.
- `recovery.json` — clean-machine/offline recovery procedure and minimum verification checks.
- `checksums.txt` — deterministic digest list for package contents.

## Exclusions
Never include plaintext credentials, API keys, OAuth tokens, signing secrets, recovery codes, private keys, sensitive personal documents, or provider session cookies.

Secret material is a separate encrypted/Owner-controlled substrate and is not required for read-only recovery.

## Determinism
- UTF-8 text only for control records.
- stable key ordering for JSON serialization;
- UTC timestamps in machine records;
- normalized newline `\n`;
- SHA-256 content digests;
- deterministic manifest ordering.

## Recovery guarantees targeted
A verified package should let a replacement control implementation determine:
1. what MULTIVERSE is trying to achieve;
2. what is currently adopted vs candidate;
3. which actions need Owner authority;
4. what work is owner-free and can continue;
5. what services/capabilities are required;
6. where evidence/artifacts are located or mirrored;
7. how to fail closed when evidence is stale/missing.

It does not by itself authorize writes, Runtime, spend, provider calls, production, credentials, or canonical migration.

## Future acceptance tests
- export twice from identical input -> byte-identical non-timestamp payloads / deterministic hashes;
- import after ChatGPT removal -> exact rules/gates/current state reconstructed;
- missing/corrupt record -> fail closed with named error;
- unknown schema version -> fail closed;
- Todoist unavailable -> Owner Command reconstructed from package;
- GitHub unavailable -> package remains readable and exposes last verified canonical revision/staleness;
- secrets scanner proves forbidden credential classes absent from package fixtures.
