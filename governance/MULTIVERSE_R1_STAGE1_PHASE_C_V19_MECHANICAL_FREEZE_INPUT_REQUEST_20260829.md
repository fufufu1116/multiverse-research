# Phase C v19 mechanical freeze input contract

Status: DRAFT / MECHANICAL BUILD INPUT ONLY / NOT LIVE AUTHORITY
Runtime: OFF

Purpose: produce the successor complete single-line artifact without hand reconstruction.

Authoritative source set (and no other Step1 delivery source):
- index 5420861580
- Part A 5420849129
- Part B 5420856829
- candidate binding 27476f7ceec9f0e7ed2fb4718cb8ac9a5b50455b / blob 4247d9deccbf6b8cb5337151b86b7eba71e28480

Mechanical builder output requirements:
1. Reconstruct exact helper/INIT/CHUNK-template/ASSEMBLE/SOURCE only from the authoritative Parts A/B and verify all published lengths/SHA-256 before use.
2. Reconstruct Step1 exact 4687-byte payload and 6252-char base64; independently verify all 13 chunk lengths/hashes.
3. Instantiate chunks 00..12 in exact order using the authoritative helper-based template.
4. Emit one UTF-8 shell line, no final LF, whose internal order is INIT -> CHUNK00..12 -> ASSEMBLE -> SOURCE and whose failure boundary prevents every later transition.
5. Do not include RETRIEVAL, OAuth, authenticated API, Step3, Step4, --apply, production mutation, main/ruleset mutation, writer/secret operation, merge, or Runtime activation in the emitted line.
6. Return the emitted artifact itself plus exact byte length and SHA-256. The artifact, not a generator, is the object to be committed and independently reviewed.
7. No live execution. Harmless local reconstruction/hash/syntax/state-machine tests only.

Core will independently Fresh-fetch and verify the returned artifact before any review request. No returned bytes are live authority until repository freeze + Independent Lab PASS + Independent Auditor PASS + Owner presentation/approval/new receipt.
