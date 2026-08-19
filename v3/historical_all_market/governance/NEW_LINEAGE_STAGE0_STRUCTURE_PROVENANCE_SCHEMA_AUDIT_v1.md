# Multiverse Keirin — NEW LINEAGE Stage 0 Structure Provenance / Schema Audit v1

Status: DESIGN AUDIT DRAFT — NOT A SCIENTIFIC FREEZE / NOT EXECUTABLE
Date: 2026-08-19 JST

## 0. Firewall

This audit uses general official KEIRIN structure/race-card documentation and existing repository schema/registry artifacts. It does not use an individual race result to select a feature or threshold.

It does NOT authorize:
- current DEV2000 C access or rescoring;
- ECON_HOLDOUT1000 opening;
- same-lineage B/C rescue tuning;
- retrospective post-race line reconstruction as PRE;
- unauthorized network collection;
- any numeric model/BUY threshold.

## 1. Official-source conclusions relevant to PRE semantics

### 1.1 Line structure is a legitimate pre-race structural object, but it is mutable

KEIRIN.JP's official guide states that line formation is central to race development and distinguishes line patterns, line leader/self-powered rider, second-position (bante) support, switching and competition for positions.

KEIRIN.JP also states that during rider introduction / leg-show / face-show / jinori, riders display or signal the line formation and order. Official material separately warns that pre-event lineup/flow forecasts are not confirmed and should be checked at the day's leg-show/newspaper.

Therefore the new lineage must distinguish at least:

- `PRE_EVENT_EXPECTED_LINE`: a pre-leg-show forecast/expected lineup;
- `LEGSHOW_OBSERVED_LINE`: an observed lineup/order at rider introduction before betting cutoff;
- `POST_RACE_RECONSTRUCTED_LINE`: prohibited as a PRE feature.

A generic race-level `prediction_timestamp` is insufficient by itself for mutable line information.

### 1.2 H is an official PRE field and should be audited for inclusion

KEIRIN.JP's race-card guide defines:
- `B`: count of leading at the final back-stretch line;
- `H`: count of leading at the home-stretch line with one lap remaining;
- `S`: count of quickly taking the position behind the pacer after the start;
- finishing-technique counts `逃/捲/差/マ`.

The guide explicitly describes H/B/S as useful for inferring initiative/position/race development.

Current repository `feature_registry_v1.csv` contains B, S and `nige/makuri/sashi/mark` but not H. H is therefore a genuine registry gap, subject to point-in-time availability proof.

### 1.3 Race regime cannot be inferred from class/sex alone

Official KEIRIN material identifies Girls KEIRIN as using international-style fixed-pacer rules, and current KEIRIN ADVANCE applies the same international-style fixed-pacer rule to some men's races. Official 2025/2026 schedules include S/A men's international-style races alongside ordinary original-rule races.

Therefore:
- `L1 => international` may often hold but must not be the schema rule;
- `male => standard line` is false in current competition;
- regime must be sourced from the actual race program/rule identity.

Provisional regime vocabulary:
- `STANDARD_ORIGINAL_LINE_KEIRIN`
- `INTERNATIONAL_FIXED_PACER`
- `UNKNOWN_OR_OTHER`

`UNKNOWN_OR_OTHER` is fail-closed for any architecture whose semantics depend on line cooperation.

### 1.4 Bank/environment are legitimate PRE context, but source/time semantics differ

Official glossary states Japanese velodrome lap lengths include 333.3m, 335m, 400m and 500m. Official race-flow guidance states riders consider wind direction, wind speed and bank lap length when choosing position.

Repository registry already contains:
- bank length;
- home straight length;
- maximum cant;
- weather;
- temperature;
- wind speed/direction.

These are not newly discovered features. They remain inactive in frozen DEV2000 and require source-specific point-in-time proof before new-lineage admission.

## 2. Minimal candidate schema — structural layer

The following is a candidate schema, not yet admitted/frozen.

### 2.1 Race identity / action timing

- `race_id`
- `prediction_timestamp`
- `decision_timestamp`
- `decision_cutoff_rule_id`

`prediction_timestamp` = model computation/reference cutoff.
`decision_timestamp` = latest information time allowed for the actual BUY/NO-BET action.

Any decision input must satisfy both PRE availability and decision availability.

### 2.2 Race regime

- `race_regime`
- `race_regime_source`
- `race_regime_source_timestamp`
- `race_regime_raw_provenance_sha`

Do not derive regime solely from `class`, sex, venue, or historical habit.

### 2.3 Line observation

- `line_group_id`
- `line_position`
- `line_size`
- `is_singleton`
- `num_lines`
- `line_source`
- `line_snapshot_timestamp`
- `line_observation_type`
- `line_raw_provenance_sha`

`line_group_id` is a within-race grouping key only. Its numeric/string identity must not enter the model as an ordinal/categorical strength signal.

`line_position` candidate convention:
- 0 = head/front
- 1 = second/bante
- 2 = third
- 3+ = rear position in the same line

`is_singleton` should be deterministic from the verified line structure (`line_size == 1`) but may be materialized for explicit interaction/audit use.

### 2.4 Rider tactical PRE

Existing:
- `style`
- `B`
- `S`
- `nige`
- `makuri`
- `sashi`
- `mark`

Candidate addition:
- `H`

For H/B/S and maneuver counts, preserve the publisher's exact rolling-window/current-card semantics and timestamp. Do not silently recompute them from future/completed races beyond the cutoff.

### 2.5 Bank/environment context

Existing registry candidates:
- `bank_length_m`
- `home_straight_m`
- `bank_cant_deg`
- `weather`
- `temperature_c`
- `wind_speed_mps`
- `wind_direction`

Venue-master fields may be treated as stable master data only with version/source provenance. Weather/wind require an observation timestamp <= decision cutoff.

## 3. Provenance acceptance matrix

### Line data

`LEGSHOW_OBSERVED_LINE`
- role: strongest direct structural PRE observation;
- required: source + snapshot timestamp + raw provenance;
- must be observed before decision cutoff;
- eligible candidate after collector/source audit.

`PRE_EVENT_EXPECTED_LINE`
- role: expected/forecast lineup;
- must remain labeled as expected, not true/observed lineup;
- eligible as a different information object only after source/timestamp audit;
- may be useful when leg-show data is unavailable, but must not be mixed silently with observed lines.

`POST_RACE_RECONSTRUCTED_LINE`
- role: post/outcome-derived reconstruction;
- model feature eligibility: PROHIBITED.

### Race regime

Official race-program/rule declaration available before the race is preferred.
If regime cannot be proven from an admissible PRE source, line-dependent model use is FAIL-CLOSED for that race.

### H/B/S/maneuver counts

Official/current race-card values are preferred. Historical replay requires proof that the stored value corresponds to the historical pre-race state rather than a present-day profile value.

## 4. Deterministic relational features allowed only after raw line admission

Candidate deterministic transforms:
- `same_line(a,b)`
- `line_position_gap(a,b)`
- `candidate_is_ahead_of(a,b)`
- `candidate_is_behind(a,b)`
- `leader_follower_relation(a,b)`
- `line_size`
- `singleton`
- `num_lines`

The raw `line_group_id` itself must not act as a predictor identity.

Derived strength/tactical features such as:
- `line_front_score_z`
- `line_support_strength`
- `line_strength_agg`
- `initiative_probability`

remain FEATURE_CANDIDATE until an exact preregistered formula/training protocol is defined.

## 5. Regime applicability contract

Every structural feature/model family must declare:

- `applicable_race_regimes`
- `inapplicable_race_regimes`
- `unknown_regime_action`

Initial candidate policy:

- C1/N1 line-based models: applicable to `STANDARD_ORIGINAL_LINE_KEIRIN` only;
- `INTERNATIONAL_FIXED_PACER`: separate control/model family or excluded until separately designed;
- unknown: FAIL-CLOSED.

This policy is a design candidate pending independent audit.

## 6. Data-quality invariants for line structure

Per race, if a line structure is admitted:

1. every active rider appears exactly once;
2. each rider has exactly one line grouping state;
3. line positions within a multi-rider line are unique and contiguous from 0;
4. `line_size` equals actual member count for every member;
5. `is_singleton == (line_size == 1)`;
6. `num_lines` equals number of distinct multi/single grouping units;
7. no withdrawn/non-active rider appears in the actionable structure;
8. snapshot time <= decision cutoff;
9. regime supports the line semantics;
10. provenance is readable and hash-addressable when canonicalized.

Any violation => FAIL-CLOSED / NO-BET or race excluded from model training depending on stage policy.

## 7. Implication for C0/C1/N1 experiment

This Stage-0 audit supports drafting the following controlled comparison:

- `C0`: existing frozen PL control;
- `C1`: comparable rider PRE plus admitted line CORE features while retaining PL order generation;
- `N1`: the same admitted PRE basis plus explicit conditional rank-2/rank-3 relational terms.

Primary test should isolate whether N1 improves conditional top-3 probability quality over C1, not whether it produces a profitable tail ticket in development.

No feature in this audit is admitted solely because of the prior 457.9x event or B failure.

## 8. Remaining unresolved P0 items before schema Freeze

1. Exact currently accessible source/transport for timestamped `LEGSHOW_OBSERVED_LINE` must be identified and audited.
2. Historical point-in-time availability of H and maneuver counts must be proven for the intended development data.
3. Exact machine-detectable `race_regime` source must be identified for prospective collection.
4. Decision timestamp must be compatible with line observation and actionable odds snapshot transport.
5. Missingness/no-bet policy for unavailable line observations must be preregistered.
6. International-regime model/exclusion policy must receive independent audit.

## 9. Next safe gate

`NEW_LINEAGE_STAGE0_SOURCE_TRANSPORT_AUDIT`

Do not freeze C1/N1 until the mutable line source and regime source can be transported with exact timestamps and provenance.

END OF AUDIT
