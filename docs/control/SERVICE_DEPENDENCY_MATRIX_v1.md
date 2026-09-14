# Service Dependency Matrix v1

Parent: Issue #432
Runtime: OFF

| Surface | Current role | End-state classification | Required replacement/recovery path | Owner-gated changes? |
|---|---|---|---|---|
| ChatGPT/OpenAI | current interactive control/advisor surface | REPLACEABLE | provider-neutral AI adapter + formal-record boot | provider credentials/spend/live calls: yes |
| GitHub | current canonical state/evidence and code host | MIGRATION_NEEDED | portable state + independent mirror + explicit canonical promotion protocol | canonical migration/account/security changes: yes |
| Todoist | temporary Owner Command UX | REPLACEABLE | normalized Owner Command model + MULTIVERSE app | no authority migration; account mutations may be Owner-gated |
| Buildkite | current independent review execution surface | REPLACEABLE_WITH_GOVERNANCE_CONSTRAINTS | independent Lab/Auditor runners on alternate CI while preserving producer separation | external pipeline/config/build actions follow existing gates |
| Netlify | current bounded web-hosting/tooling surface | REPLACEABLE | generic deployment adapter / alternate host | live deployment/domain/spend: yes |
| Tally | current bounded form/market-test surface | REPLACEABLE | generic form/intake adapter or MULTIVERSE-owned intake | publishing/live data collection may be gated |
| Google Drive | auxiliary files/docs | REPLACEABLE | portable artifacts + mirror adapters | sensitive-data/permission changes: yes |
| Gmail | communication channel | REPLACEABLE | generic messaging/notification adapter | sending/external effects: gated by authority |
| Semrush/Ubersuggest/Metricool | research/analytics equipment | REPLACEABLE | capability-based research adapters | paid spend/publishing/account mutations: yes |
| Mac/local machine | future recovery/control workspace | REQUIRED RECOVERY CLASS, DEVICE REPLACEABLE | clean-machine bootstrap from verified package + encrypted secret substrate | device/security/credential setup: yes |

## Invariants
- A connected or installed service is equipment, never authority.
- Loss of a REPLACEABLE service cannot erase canonical rules/state.
- MIGRATION_NEEDED means current authority/state is hosted there and must gain an independently tested recovery path before claiming service independence.
- Replacement must preserve authority boundaries, provenance, Lab/Auditor separation, and fail-closed behavior.
- No service credential may be treated as permission for consequential action.
