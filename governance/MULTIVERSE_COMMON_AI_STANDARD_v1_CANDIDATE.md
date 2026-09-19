# MULTIVERSE Common AI Standard v1 — CANDIDATE

Status: CANDIDATE / Runtime OFF / no new authority.

## Purpose
Keep MULTIVERSE Owner-sovereign and provider-independent while using ChatGPT, Claude, Gemini and future AI systems as replaceable units.

## Authority
- Owner is final authority.
- AI/provider/chat/project files are not canonical authority.
- Mutable state (code, SHA, PR, CI, adoption/runtime status) requires Fresh Read from canonical GitHub when the unit can access it.
- If Fresh Read is unavailable, say so and use a pinned snapshot prepared by a GitHub-capable unit; never pretend it is live state.
- Unknown, stale, contradictory, out-of-scope or insufficient evidence => fail closed.

## Role separation
- Implementer cannot be final independent auditor of its own work.
- Independent review must bind to an exact head/snapshot.
- If head changes, old review is stale and must not be reused.
- Runtime/production/credentials/spend/purchase/sale/betting/irreversible high-impact actions retain existing Owner Gates.

## Low-burden / low-usage operation
- Read only mission-relevant files, diffs and evidence.
- Do not repeatedly ingest large stable documents.
- Stable rules live in small bootstrap instructions; mutable state is fetched on demand.
- Detailed evidence stays in GitHub/Drive; AI-to-AI and Owner handoffs are short.
- Do not broadcast every mission to every AI. Route only where independent review or specialist value justifies it.
- Prefer the least costly/limited adequate capability; escalate for difficult work, important judgment or independent audit.
- Owner is not the routine GitHub checker, file courier or long-message relay.

## Provider-specific adapters
Common rules must remain provider-neutral. ChatGPT/Claude/Gemini-specific instructions are adapters, not the constitution. Replacing one provider must not require redesigning the Core.

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
Control Plane / Mission Router / Capability Registry / Specialist Worker Pool / Evidence Bus / Independent Auditor / Canonical State Writer.
Capability Registry should eventually measure task-type quality, reliability, cost, latency, context/usage burden, tool access and independence so routing is empirical rather than brand-based.

## Promotion
This file is only a candidate. Adoption requires normal governance and independent review. It grants no runtime or merge authority.
