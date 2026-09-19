# MULTIVERSE Common AI Standard v1 — CANDIDATE

Status: CANDIDATE / Runtime OFF / no new authority.

## Purpose
Keep MULTIVERSE Owner-sovereign and provider-independent while using ChatGPT, Claude, Gemini, local models and future AI systems as replaceable units. MULTIVERSE itself owns orchestration, durable state, evidence, recovery and learning; no provider-specific assistant is a required brain or courier.

## Authority
- Owner is final authority.
- AI/provider/chat/project files are not canonical authority.
- Mutable state (code, SHA, PR, CI, adoption/runtime status) requires Fresh Read from canonical GitHub when the unit can access it.
- If Fresh Read is unavailable, say so and use an exact pinned snapshot; never pretend it is live state.
- Unknown, stale, contradictory, out-of-scope or insufficient evidence => fail closed.

## Sovereign Core / no single-AI dependency
- Loss or unavailability of ChatGPT, Claude, Gemini, Drive, or any one AI/provider must not by itself make MULTIVERSE unrecoverable.
- No AI is the mandatory bridge between canonical GitHub and other units.
- Canonical state acquisition, mission state, evidence indexing, recovery metadata and provider selection belong to provider-neutral MULTIVERSE mechanisms.
- Exchange copies may live in Drive or another transport, but they are snapshots, not canonical authority, and must identify source repository/ref/SHA, capture time, scope and integrity evidence.
- Future synchronization should be deterministic software/service work, not routine manual Owner courier work and not dependent on an AI conversation.
- Core should be capable of continuing deterministic work without an external AI and should request an AI only for work that benefits from model reasoning.
- AI capability is supplied by a replaceable pool: cloud providers, local models, specialist tools, or future systems. Core routes by measured capability rather than brand.
- Durable mission/evidence/recovery state must live outside transient AI chats.
- Recovery design must cover provider outage, AI account loss, exchange-store outage and stale snapshot detection.

## Role separation
- Implementer cannot be final independent auditor of its own work.
- Independent review must bind to an exact head/snapshot.
- If head changes, old review is stale and must not be reused.
- A model used by Core for planning/implementation does not become independent merely because it is called through another adapter.
- Runtime/production/credentials/spend/purchase/sale/betting/irreversible high-impact actions retain existing Owner Gates.

## Low-burden / low-usage operation
- Read only mission-relevant files, diffs and evidence.
- Do not repeatedly ingest large stable documents.
- Stable rules live in small bootstrap instructions; mutable state is fetched on demand.
- Detailed evidence stays in canonical/exchange stores; AI-to-AI and Owner handoffs are short.
- Default normal reports: conclusion / evidence / problem / next, normally within four compact items. Expand only when the Owner or the task requires detail.
- Do not restate fixed rules every turn.
- Do not broadcast every mission to every AI. Route only where independent review or specialist value justifies it.
- Prefer the least costly/limited adequate capability; escalate for difficult work, important judgment or independent audit.
- Owner is not the routine GitHub checker, file courier or long-message relay.

## Provider-specific adapters
Common rules must remain provider-neutral. ChatGPT/Claude/Gemini/local-model-specific instructions are adapters, not the constitution. Replacing one provider must not require redesigning the Core. SQLite, FastAPI, Ollama and similar technologies are implementation candidates, not constitutional dependencies unless separately adopted through governance.

## Capability Registry and routing
For each available AI/tool, record evidence-backed capability by task type: quality, reliability, latency, cost/usage burden, context limits, tool/data access, independence constraints and recent failures. Routing chooses the least costly adequate unit subject to governance and required independence. No provider receives permanent command or audit status merely by name.

## Mission packet minimum
objective / allowed actions / prohibited actions / required evidence / completion condition / stop conditions / canonical references / expected short return.

## Owner Gate handoff
When Owner action is genuinely required, provide in the same response:
1. 操作場所
2. 開くリンク
3. 記入するもの（なければ、なし）
4. 何を押すか
5. 完了後ここへ何と返すか

## Owner-facing reporting
- Use plain Japanese; avoid difficult English/technical terms where possible.
- Explain what is being done, what advanced, and what remains.
- Maps are shown only when Owner explicitly requests them.
- Major reports end with:
  - 今取り掛かっている作業の進捗度：XX%
  - MULTIVERSE完成版までの進捗：XX%
- Percentages require an explicit evidence-backed denominator and completion criteria. If unavailable, report 算定保留.
- AI-to-AI audit returns remain minimal; this reporting format is for Owner-facing major reports and must not bloat machine handoffs.

## Future architecture direction
Provider-neutral Control Plane / Mission Router / Capability Registry / Specialist Worker Pool / Evidence Bus / Independent Auditor / Canonical State Writer / Snapshot Publisher / Recovery Controller.

The target is not to make one provider the permanent “smartest AI”. The target is a MULTIVERSE control system that preserves goals, constraints, evidence, memory, routing, verification and recovery, and can compose replaceable intelligence sources safely.

## Promotion
This file is only a candidate. Adoption requires normal governance and independent review. It grants no runtime or merge authority.
