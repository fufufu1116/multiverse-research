# Multiverse Keirin — NEW LINEAGE Stage 0 Source Transport / Rights Audit v1

Status: DESIGN / SOURCE AUDIT — NOT A SCIENTIFIC FREEZE / NOT EXECUTABLE
Date: 2026-08-19 JST

## 0. Firewall

This audit establishes what can be treated as a candidate PRE/decision-time source and what remains blocked. It does not authorize bulk collection, protected outcome access, current DEV2000 C use, or ECON_HOLDOUT1000 opening.

## 1. Public official transport surface exists, but semantics are heterogeneous

KEIRIN.JP / related official venue pages expose Data Plaza URL families keyed by race date / venue / race number, including historically and currently referenced forms such as:

- `raceall?KCD=<venue>&KBI=<yyyymmdd>`
- `racemember?KCD=<venue>&KBI=<yyyymmdd>&RNO=<race>`
- `raceprogram?KCD=<venue>&KST=<yyyymmdd>`
- `entrymember?KCD=<venue>&KST=<yyyymmdd>`

Official venue pages link into `raceall` and in some cases explicitly state that the destination is available only on the race day / from the race day.

Implication:
- a deterministic venue/date URL convention is a plausible transport mechanism;
- availability is time-scoped and cannot be assumed for arbitrary advance/historical replay;
- any prospective collector must log actual fetch timestamp, HTTP status, source URL and raw payload identity.

## 2. Line observation remains the main transport blocker

Official KEIRIN guidance confirms that rider introduction / leg-show / face-show / jinori is where riders show or signal line formation and order.

However this audit has NOT established a stable official machine-readable field in KEIRIN.JP Data Plaza that directly exposes the observed leg-show line grouping/order as structured data.

Therefore:

- `line_group_id / line_position / line_size` remain scientifically attractive but transport-unproven;
- a pre-event forecast lineup is not equivalent to an observed leg-show lineup;
- a post-race reconstruction from video/report is prohibited as a PRE input;
- no line-dependent C1/N1 execution is authorized until a lawful, timestamped, reproducible transport route is proven.

## 3. H/B/S and maneuver-count semantics are official; historical point-in-time transport still needs proof

KEIRIN.JP official race-card documentation defines B, H, S and `逃/捲/差/マ` and explains their race-development meaning.

Existing NEXTGEN registry already includes B/S and maneuver counts but not H.

Remaining transport question:
- for each intended development/prospective race, can the exact historical/current race-card values be captured before the decision cutoff and stored with provenance?

Current player/profile values must never be backfilled into historical races without proof that they equal the historical pre-race state.

## 4. Race-regime transport is P0

Official KEIRIN/JKA material confirms that in 2025-2026 men's KEIRIN ADVANCE and some rookie races use `先頭固定競走（インターナショナル）`, while ordinary men's races may use `先頭固定競走（オリジナル）`; Girls KEIRIN uses the international-style rule.

Therefore class/sex is insufficient as the source of truth.

Candidate transport order:

1. official race-program / event-program rule declaration;
2. official event metadata / official schedule label when unambiguous;
3. otherwise `UNKNOWN_OR_OTHER` and fail closed for line-dependent architecture.

A machine-detectable per-race regime field has NOT yet been proven. This remains unresolved before schema Freeze.

## 5. Actionable odds boundary

Official KEIRIN internet-betting guidance states that normal same-day internet betting is accepted from the morning until a fixed number of minutes before the announced scheduled start time (the cited current guide states three minutes before).

This establishes an important execution distinction:

- `PRE_AVAILABLE` does not automatically mean `DECISION_AVAILABLE`;
- closing/final odds observed after the live decision cutoff are invalid BUY inputs;
- a future market model must use an odds snapshot actually captured before the frozen action cutoff;
- final payout/settlement remains an outcome-side artifact used only after the betting decision is frozen.

No numeric decision margin is frozen in this audit. A future protocol must choose and preregister a safe cutoff strictly compatible with the official betting window and the latency of line/odds collection.

## 6. Odds snapshot cadence / historical archive is unresolved

This audit found official odds display and internet betting access, but did NOT find an official public specification guaranteeing:

- odds update cadence;
- immutable timestamped historical odds snapshots;
- a public archival API for arbitrary pre-race times.

Therefore a future `market_snapshot_tminusX` feature is transportable only if the collector itself captures the snapshot at the preregistered time from an authorized source, or a licensed historical vendor supplies timestamped data.

Historical closing odds alone remain unsuitable as a live BUY feature unless they were truly observable by the decision cutoff.

## 7. Rights / ToS / collection boundary

KEIRIN.JP's current site policy states that content/information is protected by copyright and may not be reproduced or repurposed beyond uses allowed by law such as private use or quotation without permission.

This audit found no official public open API / open-data license for bulk race-card / line / odds data.

Consequences:

- public page visibility does NOT by itself authorize automated bulk harvesting, archival, redistribution or commercial use;
- no rate-limit/WAF/authentication/CAPTCHA avoidance is permitted;
- prospective collection remains `NOT_AUTHORIZED` until an allowed source route is established;
- preferred routes are direct permission/licensing, an official/authorized data feed, or an authorized third-party source whose terms permit the intended research/operational use.

JKA publicly describes VIS / 2028VIS data-integration systems and has separately procured big-data research infrastructure, but those notices do not constitute a public data license or API for this project.

## 8. Source classes for future governance

Candidate source classes:

### `OFFICIAL_PUBLIC_VIEW_ONLY`
Official page visible to a normal user, but no bulk-use license proven.
Use: manual research / semantic verification only unless rights are clarified.

### `OFFICIAL_AUTHORIZED_FEED`
Official/JKA/venue feed or permission with explicit permitted use.
Use: preferred for production/prospective collection.

### `AUTHORIZED_THIRD_PARTY_FEED`
A provider authorized to distribute the relevant pre-race data with terms compatible with this research/use.
Use: allowed after source and timestamp audit.

### `PUBLIC_FORECAST_SOURCE`
Pre-race specialist/news forecast lineup or comments, timestamped and permitted.
Use: separate expected-information object, never mislabeled as official observed line.

### `POST_RACE_RECONSTRUCTION`
Video/report/results reconstruction.
Use as model input: PROHIBITED.

## 9. Collector acceptance requirements before authorization

Any future collector must be preregistered with:

- source/provider identity;
- legal/terms basis for collection/storage/use;
- exact endpoint/page/feed semantics;
- prediction/decision cutoff;
- clock/timezone source;
- raw response timestamp;
- HTTP status / retry policy;
- no bypass behavior;
- rate policy compliant with provider rules;
- raw payload SHA-256;
- parser version/blob identity;
- missingness/fail-closed behavior;
- immutable race identity;
- result/payout namespace isolation;
- proof that the same semantics are available in development, final validation and live operation.

## 10. Current verdict by candidate feature family

- `race_regime`: STRUCTURALLY_REQUIRED / TRANSPORT_NOT_YET_FULLY_PROVEN
- `line_group_id/position/size`: HIGH-VALUE CORE CANDIDATE / OBSERVED-LINE TRANSPORT NOT YET PROVEN
- `H`: CORE FEATURE CANDIDATE / HISTORICAL POINT-IN-TIME TRANSPORT NOT YET PROVEN
- `nige/makuri/sashi/mark`: EXISTING NEXTGEN CANDIDATES / POINT-IN-TIME TRANSPORT TO AUDIT
- `bank_length/home_straight/cant`: LIKELY STABLE MASTER DATA / SOURCE VERSIONING NEEDED
- `weather/wind`: PRE CANDIDATES / OBSERVATION TIMESTAMP REQUIRED
- `market odds snapshot`: DECISION FEATURE CANDIDATE / SNAPSHOT CAPTURE RIGHTS + TIMING REQUIRED

## 11. Next gate

`NEW_LINEAGE_STAGE0_SOURCE_RIGHTS_AND_PROVIDER_SELECTION`

Before any collector implementation or untouched prospective collection:

1. identify a lawful/authorized provider path for structural PRE + racecard + odds;
2. prove timestamp semantics and regime/line coverage;
3. only then draft/approve collector implementation;
4. only after source/collector audit pass may prospective collection be proposed for authorization.

Current DEV2000 C remains untouched for the new lineage.
`ECON_HOLDOUT1000 = SEALED`.

END OF AUDIT
