# Phase C v18 authority correction

Status: FAIL_CLOSED / REVIEW ONLY / NOT LIVE AUTHORITY
Runtime: OFF

Core Fresh Read discovered a material authority mismatch before freezing or delivering any live action.

The v18 generator at commit a4cf0d77b7c409e53fb34183b0ace05e0f106a3a binds manifest comments 5420731105 / 5420744033. Those are historical delivery evidence and are superseded for future live delivery.

The sole-authoritative helper-based v2 manifest is:
- index: PR #74 comment 5420861580
- Part A: PR #74 comment 5420849129
- Part B: PR #74 comment 5420856829

Fresh metadata from that authority includes:
- Step1 decoded: 4687 bytes / SHA-256 bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74
- Step1 base64: 6252 chars / SHA-256 f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2
- verified helper: 6238 bytes / SHA-256 8bf1a555e80241c82d240eee3bdda3a885a1dbaac4c8692b80d13c47c9f502b8
- INIT: 4291 bytes / SHA-256 3f21f89884757dab2728d4be376f19a2bbe4aa3396162434e1822ce2b36375d2
- CHUNK template: 382 bytes / SHA-256 7346430c248d0e9f3eed92c7fda4cb1abc342fb7a7a803467afcbfc3f899f15e
- ASSEMBLE: 293 bytes / SHA-256 909df243fbf0e31adcbc2de8018796ee2a4aa5fb1fb8bce58c3872b5ef74f871
- SOURCE: 1716 bytes / SHA-256 cb34865720b2973b1226b8afa81074098c246c1308d0797da29490df6f251ecd

Therefore v18 is not eligible for Auditor progression, Owner presentation, live delivery, Codespace creation, OAuth, authenticated API, Step4, --apply, production/main/ruleset/writer-secret mutation, merge, or Runtime activation regardless of its structural preservation result.

Successor remediation must bind only 5420861580 + 5420849129 + 5420856829 and must freeze the complete emitted one-line action as repository bytes with byte length, SHA-256, no-final-LF status, blob SHA and immutable commit. Delivery must Fresh-fetch that frozen artifact and mechanically verify it; no local regeneration is live authority.
