# Multiverse vNext — Batch 1 Foundation Design v0

Status: WORKING CANDIDATE — REVIEW BRANCH — NOT ACCEPTED / NOT FROZEN  
Revision: VAULT-HARDENED after PR #2 MATERIAL_BLOCK review  
Date: 2026-08-20 JST

## 0. Scope and Keirin firewall

Batch 1 builds the minimum durable Multiverse vNext spine while Keirin is safely paused.

It does **not**:
- open `ECON_HOLDOUT1000`;
- score or reuse DEV2000 C for new-lineage rescue;
- change validation membership or trial counts;
- access protected RESULT/PAYOUT material;
- authorize new spending;
- replace constitutional governance;
- formally accept, freeze, promote, or release vNext.

The protected restart point is a versioned immutable-candidate receipt. Once accepted, that receipt is **supersede-only** and must never be edited in place.

## 1. Canonical authority and recovery roots

### I1 — CHAT LOSS != PROJECT STATE LOSS
Loss of chat history must not destroy the ability to reconstruct project state.

### I2 — One logical canonical authority, multiple physical recovery roots
There is one logical canonical authority for accepted small state/code/governance: the verified GitHub canonical lineage.

Physical recovery roots are intentionally plural:
- GitHub canonical repository;
- Google Drive recovery mirror for accepted recovery packages;
- optional iPhone cold snapshot at major accepted milestones.

A mirror is **never** allowed to self-promote into canonical authority merely because GitHub is unavailable.

### I3 — Newer state is ancestry/supersession based, not timestamp based
A state is newer only when justified by:
1. verified Git commit ancestry;
2. monotonic `state_generation`;
3. explicit parent and supersession references.

Timestamps are metadata, not authority.

### I4 — Fail closed
Ambiguity involving holdout, permission, mutable state identity, source timing, or Freeze identity causes refusal to mutate/promote until resolved.

## 2. Mutable STATE CAS / anti-rollback protocol

The stable Current State path is mutable, but every update must use compare-and-swap semantics.

Required fields:
- `state_generation`;
- `parent_state_git_blob_sha`;
- `supersedes_state_ref`;
- `write_precondition.expected_current_state_blob_sha`;
- `write_precondition.expected_canonical_main_head`;
- `write_precondition.expected_generation`;
- `canonical_precedence_rule`.

Writer algorithm:

1. Fetch canonical `main` HEAD and the current-state path blob.
2. Compare both with the state's declared preconditions.
3. Reject if either differs.
4. Require `new_generation = old_generation + 1`.
5. Require the new state to name the exact old blob as parent/superseded state.
6. Perform the GitHub update using the old blob SHA as the write precondition.
7. Read back the new blob/commit and record it in the next immutable checkpoint/recovery manifest.
8. Never use timestamp ordering to override ancestry.

This is the mandatory stale-writer behavior:
`STALE_PARENT_OR_HEAD -> FAIL_CLOSED_NO_WRITE`.

## 3. Artifact mutability discipline

`MUTABLE_CAS_POINTER`
- current-state pointer;
- stable bootstrap locator;
- active working pointer when required.

`IMMUTABLE_AFTER_ACCEPTANCE_SUPERSEDE_ONLY`
- Keirin pause receipts;
- acceptance receipts;
- recovery test receipts;
- material decision/audit receipts.

`WORKING_CANDIDATE`
- design drafts and review-branch artifacts before acceptance.

Immutable identity is externally anchored. An immutable receipt does not contain a circular self-hash; its exact `{repo, path, commit, git_blob_sha, sha256, mutability}` tuple is pinned by Current State, manifest, or a later acceptance receipt.

## 4. Deterministic bootstrap

Stable locator candidate:
`MULTIVERSE_BOOTSTRAP.md`

Recovery from **repository locator only**:

1. Read `MULTIVERSE_BOOTSTRAP.md` from `main` when present.
2. Read the referenced Current State.
3. Verify its generation, parent/supersession fields and pinned artifact identities.
4. Load the recovery manifest/receipt locator.
5. Load the Keirin pause receipt only as governance metadata; do not open protected data.
6. If vNext has not yet merged to main, list open PRs and select the single PR explicitly marked `[ACTIVE-VNEXT]`; verify its base SHA against current main before reading its branch Current State.
7. If branch state is unavailable, use the non-authoritative Drive recovery package only to reconstruct the last mirrored working state, then reconcile against GitHub history before any write.
8. If there is ambiguity between two candidate active states, stop mutation and report `RECOVERY_AMBIGUOUS`.

The bootstrap target is project-state reconstruction, not verbatim deleted-chat recovery.

## 5. Physical recovery architecture

### GitHub
Role: `CANONICAL_AUTHORITY_FOR_ACCEPTED_SMALL_STATE_CODE_GOVERNANCE`

Current observed main head at Batch-1 pause:
`ea2559b429bf04a1bd0acee13412ed783e92be5d`

Observed assurance:
- branch protection: not enabled;
- commit signature: unsigned.

Those facts reduce assurance but do not by themselves imply compromise. Accepted commit identity must therefore be externally anchored in a second physical root until stronger repository controls are adopted.

### Google Drive
Folder:
`MULTIVERSE_VNEXT_RECOVERY`
Folder ID:
`1-9uS0-_6oXj9aFbeykonk5-8ss6SpkH4`

Role:
`NON_AUTHORITATIVE_RECOVERY_COPY`

The Drive recovery package must contain:
- raw UTF-8 copies of material bootstrap/current-state/design/receipt artifacts;
- `SHA256SUMS.txt`;
- a manifest naming the source Git commit;
- no protected Keirin holdout/result/payout bytes.

### iPhone cold snapshot
Optional at major accepted milestones. Not required for Batch-1 acceptance if GitHub + verified Drive restore is demonstrated.

## 6. Recovery evidence requirements

Acceptance evidence must include:

1. **Stale-write/CAS test**  
   S1 → S2 is written, then a writer based on S1 attempts update and is rejected without mutation.

2. **Immutable-receipt test**  
   A modified receipt copy fails pinned blob/SHA-256 identity.

3. **New-chat bootstrap test**  
   Repository locator only, zero useful chat history, reconstructs current phase, canonical commit, protected boundaries and Keirin resume gate.

4. **Dual-root restore test**  
   A missing GitHub working artifact or simulated GitHub unavailability can be reconstructed from Drive with SHA-256 verification; mirror stays non-authoritative.

5. **Newer-state precedence test**  
   A simulated later legitimate canonical Keirin state supersedes the pause receipt; stale receipt cannot roll it back.

6. **Working-branch loss test**  
   Loss of runtime/branch does not cause an accepted state to be mistaken for unfinished work, and last mirrored working state is discoverable.

7. **Firewall regression test**  
   Bootstrap/restore reads governance metadata only and does not require opening sealed/protected Keirin evidence.

## 7. Evidence / Source Intelligence Engine

Source tiers:
- `A` primary/authoritative;
- `B` strong secondary/corroboration;
- `C` reference/orientation;
- `D` community/experience;
- `E` unverified signal.

Community sources are sensors for tacit knowledge, failure modes, minority views and hypothesis discovery; they are not automatic proof.

Material discovery pipeline:
`DISCOVER -> CLAIM_EXTRACT -> SOURCE_RECORD -> CLASSIFY -> PRIMARY_SEARCH -> INDEPENDENT_CORROBORATION -> CONTRADICTION_SEARCH -> MEASURABLE_HYPOTHESIS -> TEST/AUDIT -> PROMOTE/REJECT/UNKNOWN`

A Source Object must separate:
- `acquisition_purpose_at_time`;
- `later_research_use`;
- `applicable_terms`;
- `permission_basis`;
- `redistribution_constraints`.

Later research use may not rewrite the historical acquisition purpose or imply permission that did not exist.

No authentication, CAPTCHA, WAF, or rate-limit bypass.

## 8. Knowledge objects

Do not hand the Owner a source pile.

Distill:
`RAW_SOURCE -> CLAIM -> SUPPORT/CONTRADICTION -> CONFIDENCE -> KNOWLEDGE_OBJECT -> RULE/HYPOTHESIS/DECISION`

Important claims retain both supporting and contradicting evidence.

## 9. AI Interop / Conversation Bus

Direct realtime AI-to-AI conversation is optional.

Exchange object flow:
`STATE -> REQUEST -> EVIDENCE -> REVIEW -> DECISION -> RESPONSE`

Preferred transport:
1. GitHub for small durable state/reviews;
2. Drive for heavy/recovery bundles;
3. manual chat relay only as a temporary fallback;
4. Replit automation only after repeated relay burden is empirically observed.

Routing names shown to Owner:
- Core = **司令塔**
- Vault = **記録庫**
- Lab = **検証室**
- Auditor = **監査室**
- Gemini Core = **Gemini司令塔**
- Gemini Vault = **Gemini記録庫**
- Gemini Lab = **Gemini検証室**
- Final Auditor Gemini = **Gemini監査官**
- Claude = **Claude査問**
- Source Intelligence = **探索網**
- Recovery = **復旧網**

Machine identifiers remain English for compatibility.

## 10. Self-audit and Owner burden

Every Material Batch checks:
- canonical drift / stale write;
- missing SHA/provenance;
- SPOF / restore evidence;
- source monoculture / confirmation bias;
- unnecessary tool/file proliferation;
- unnecessary paid dependency;
- iPhone-hostile manual relay;
- benchmark/failure gaps;
- simpler/faster/cheaper alternatives;
- role-independence gaps.

Classification:
- `NO_MATERIAL_ISSUE`
- `MINOR_AUTOFIX_CANDIDATE`
- `MATERIAL_REVIEW_REQUIRED`
- `RECOVERY_RISK`
- `COST_GATE`
- `SOURCE_PERMISSION_GATE`
- `CONSTITUTIONAL_OWNER_GATE`

Owner should not manually compare SHAs, route roles, or retype long prompts.

## 11. Cost / portability

`NEW_SPEND_DEFAULT = NO`.

Use existing ChatGPT, Gemini plan, Claude free quota, GitHub, Drive, Replit and open formats first.

Preferred portable formats:
TXT, Markdown, JSON, CSV, ZIP and SHA-256 manifests.

If fresh external facts are unavailable:
`UNKNOWN`, `STALE`, or `OFFLINE_UNAVAILABLE`.
Never fabricate.

## 12. Batch-1 acceptance boundary

Batch-1 remains **NOT ACCEPTED** until:
- record identities are pinned;
- anti-rollback CAS test passes;
- deterministic bootstrap test passes;
- GitHub + Drive dual-root restore passes;
- recovery package and restore receipt exist;
- Keirin firewall regression passes;
- 記録庫 clears the canonical/recovery material block;
- 検証室 attacks complexity, failure modes, cost and iPhone burden;
- 司令塔 incorporates findings;
- only then is 監査室 asked for formal acceptance/release review.

Current routing:
`司令塔修正 -> 記録庫再確認 -> 検証室 -> 司令塔改訂 -> 監査室(acceptance candidate only)`

END
