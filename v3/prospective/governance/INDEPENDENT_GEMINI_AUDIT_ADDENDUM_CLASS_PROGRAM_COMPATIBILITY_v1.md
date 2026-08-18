# Independent Gemini Audit Addendum — Race-Level Class / Program Compatibility

This addendum is governance/audit-only. It does not alter model weights, source set, selection rule, scientific trial counts, Shadow250 membership, or authorization.

## Official race-program semantics to verify

Current KEIRIN.JP guidance and 2026 program tables distinguish race classes as follows:

- A級3班 = A級チャレンジ / A3 race program.
- A級1・2班 = A1/A2 race program.
- S級 = S-class race program; FI may contain both S-class races and A1/A2 races in the same meeting, but S-class and A-class riders do not run in the same race.
- Therefore a normal race-level entrant set must not contain impossible cross-program mixtures such as A3+A1/A2, A3+S, or A1/A2+S.
- SS/S1/S2 mixtures may exist within an S-class race; A1/A2 mixtures may exist within an A1/A2 race; A3 races are A3-class; L1 is a separate Girls program.

## Recovered model behavior

`B1A_RECONSTITUTED_v1_IMPLEMENTATION.py` computes logits and a softmax separately within each `rec['entrants']` race record. It never intentionally compares riders from different race_ids.

The frozen B1a class feature set is:
`SS, S1, S2, A1, A2, A3, L1`.

Recovered final beta values include:
- class_SS = 1.0770873580301035
- class_S1 = -0.12658801568020364
- class_S2 = -0.9504993423499002
- class_A1 = 0.10862511799550383
- class_A2 = -0.10862511799550574
- class_A3 = approximately 0 (`4.991005121158697e-16`)
- class_L1 = approximately 0 (`-1.446593378458555e-16`)

Interpretation to audit: when every entrant in a race has the same class category (e.g. A3-only or L1-only), the corresponding class logit contribution is constant across all entrants and cancels under race-level softmax. A1/A2 and SS/S1/S2 differences can affect relative probabilities only inside race programs where those class mixtures are legitimately possible.

## Identified parser guard gap

Current candidate `v3/prospective/tamano_racecard_row_parser_v1.py` validates each row class independently against `SS|S1|S2|A1|A2|A3|L1`, but does NOT currently enforce a race-level admissible class/program composition.

Therefore a malformed extraction could theoretically emit an impossible mixed class set under one race_id and still pass the current category check.

## Mandatory additional hostile-audit questions

1. Must first prospective use include an explicit race-level class/program compatibility gate?
2. Should admissible class sets be exactly:
   - S program: subset of `{SS,S1,S2}`
   - A1/A2 program: subset of `{A1,A2}`
   - A3 program: exactly `{A3}`
   - Girls program: exactly `{L1}`
   with all cross-program mixtures rejected fail-closed?
3. Is meeting-level grade/program metadata required to distinguish A3 from A1/A2/S races, or is entrant-class-set validation sufficient under the frozen Tamano racecard semantics?
4. If the parser receives an impossible mixture such as `{A3,A2}` or `{A1,S2}`, must the race be `PRE_INELIGIBLE_SOURCE_GAP` / QUARANTINE with no replacement after outcome?
5. Does adding this guard constitute a safety completion of the candidate parser before its first Freeze, or an `adapter change` under `SHADOW250_SOURCE_SET_FINAL_FREEZE_v1` requiring a NEW Shadow universe? Resolve explicitly before any selected race.
6. Verify that no training or prediction step creates synthetic cross-class matchups: each probability normalization must remain strictly race-local.

Until this is independently resolved, do not treat race-level class/program compatibility as proven by the candidate parser alone.
