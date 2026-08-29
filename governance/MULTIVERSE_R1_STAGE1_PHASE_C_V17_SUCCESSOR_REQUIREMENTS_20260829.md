# Phase C v17 successor exact requirements

Status: DRAFT / REVIEW ONLY / NOT AUTHORIZED
Runtime: OFF

Binding review source: Independent Lab PR #74 comment 5459644897.
Authoritative manifests: PR #74 comments 5420731105 (Part A) and 5420744033 (Part B).

A successor single-paste candidate MUST preserve, in exact authoritative order:

1. INIT: fresh fixed memory-backed root; 0700/current-owner/root trust; 0600 evidence.ndjson created O_EXCL|O_NOFOLLOW; fsync+reread; exact binding-bearing INIT_PASS.
2. CHUNK 00..12: prior complete journal/root/trusted-chunk validation before each chunk; each chunk-NN.b64 0400 O_EXCL|O_NOFOLLOW; fsync+reread/hash; CHUNK_ACCEPTED append+fsync+reread before advancing.
3. ASSEMBLE: exact complete journal/root/chunk prerequisites; assembled base64 and decoded invariant checks; exclusive/nofollow durable artifacts; ASSEMBLED_INTEGRITY_PASS append+fsync+reread before success.
4. SOURCE: reverify evidence; durable SOURCE_START before same-parent-shell source; preserve original source RC; durable SOURCE_COMPLETE only on zero; fixed durable nonsecret fallback evidence on journal/event/source/parent-shell failure; fail closed.
5. RETRIEVAL: retain the fixed nonsecret evidence root/failure artifacts needed by the reviewed read-only retrieval contract; preserve decoded cleanup boundary only after successful source completion.
6. Preserve every binding, exact root-set, type/owner/mode, length/hash and journal schema/order check from the authoritative manifests. In-memory-only substitution is forbidden.
7. Freeze the COMPLETE emitted one-line action itself as exact UTF-8 bytes + SHA-256 + immutable repository blob/commit. No post-review payload reconstruction may be required for delivery.
8. Harmless regression coverage must include corrupted/missing journal, out-of-order/duplicate event, unexpected root file, corrupted prior/current chunk, preexisting chunk/assembled/decoded paths, assembled mismatch, source nonzero, source/event-commit failure, and retrieval of failure evidence; each must prove no forbidden next transition.

No live execution or production mutation is authorized.
