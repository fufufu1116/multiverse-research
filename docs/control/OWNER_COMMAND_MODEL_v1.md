# MULTIVERSE Owner Command Model v1

Parent roadmap: Issue #432
Control basis: Issue #394

## Purpose
Provide one provider-neutral Owner-facing command model that can be rendered by Todoist today and by the future MULTIVERSE app without making either service authoritative.

## Authority
- GitHub canonical remains authoritative until separately reviewed/adopted migration.
- This model is a projection, not an authority expansion.
- Runtime remains OFF.
- Credentials never imply authority.

## Owner experience
The default Owner view contains only items that require genuine Owner action, final decisions, or deadlines. Internal research/test/CI status is suppressed unless it changes a decision or creates a blocker.

When Owner action is required, the payload carries the complete five-part instruction:
1. 操作場所 (`location`)
2. 開くリンク (`link`)
3. 記入するもの (`input`)
4. 何を押すか / 実行するか (`action`)
5. 完了後ここへ何と返すか (`reply_with`)

## Normalized item kinds
- `TASK`: actionable work item
- `OWNER_GATE`: genuine authority/manual gate
- `FINAL_DECISION`: evidence-ready Owner decision
- `DEADLINE`: deadline/prerequisite with potential consequence
- `STATUS`: lane/system state
- `RECOVERY`: service/recovery action or state

## Status model
`NOW`, `NEXT`, `WAITING`, `BLOCKED`, `READY_FOR_DECISION`, `DONE`.

`WAITING` is never a global stop. Other owner-free queues continue under Control #394.

## Todoist temporary projection
Todoist is a replaceable UI prototype only.

Suggested mapping:
- NOW + owner_action_required=true -> `今やる`
- FINAL_DECISION / READY_FOR_DECISION -> `最終決断`
- DEADLINE -> `期限あり`
- WAITING -> `待機中`
- DONE -> `完了・記録`

Todoist object IDs are service-specific projection metadata and must never become canonical IDs.

## Future app information architecture
The MULTIVERSE app should render the same model through:
- Today
- Roadmap
- Decisions
- Deadlines
- Status
- Recovery

The app consumes normalized control data rather than ChatGPT chat state.

## Offline / degraded mode
A future portable package must be sufficient for read-only operation when ChatGPT, GitHub, Todoist, or a provider is unavailable. The degraded view must retain:
- last verified canonical revision and timestamp;
- current roadmap/stage;
- fixed rules and authority boundaries;
- pending Owner Gates/final decisions/deadlines;
- artifact/provenance pointers;
- recovery instructions;
- explicit stale/offline indicator.

No degraded/offline mode may silently infer new authority.

## Service-independence invariants
1. Canonical IDs are generated independently of Todoist/GitHub issue IDs/provider IDs.
2. Every item carries evidence refs and explicit authority state.
3. Owner-action instructions are complete when required.
4. Internal status noise is not promoted into Owner work.
5. Projection loss (for example Todoist outage) cannot delete canonical task/roadmap state.
6. Chat loss cannot delete project state.
7. Provider substitution does not change governance semantics.
8. Runtime, spend, credentials, production and irreversible effects remain separately gated.

## Candidate scope
This v1 Candidate contains only schema/model/validation documentation and regressions. It does not deploy an app, migrate canonical authority, activate Runtime, call providers, handle credentials, or spend money.
