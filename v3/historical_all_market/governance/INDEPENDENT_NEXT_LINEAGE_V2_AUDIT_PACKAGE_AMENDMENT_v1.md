# Independent Next-Lineage v2 Audit Package — Amendment v1

Status: AUDIT PACKAGE AMENDMENT — NOT SCIENTIFIC FREEZE
Date: 2026-08-19 JST

This amendment must be read with:
`INDEPENDENT_NEXT_LINEAGE_V2_AUDIT_PACKAGE.md`
commit `cbb0557169074ee483e2784cddad5f1225a05b09`.

## Updated implementation references

The probability-object implementation was extended after the base package was written.

Use the following latest reference instead of the older commit printed in Section 7 of the base package:

- `v3/historical_all_market/new_lineage/probability_object_contract_v1.py`
- latest update commit: `7528981977302cd187cde2814cf40d08a234d8cc`

The extension adds deterministic frame-market aggregation from the same ordered top-3 source via a race-card `car_to_frame` mapping. Same-frame outcomes are retained naturally, consistent with official 2枠単/2枠複 same-frame ('ゾロ目') semantics where applicable.

Additional implementation artifacts:

- C0/C1/N1 source-independent probability core:
  `v3/historical_all_market/new_lineage/top3_architecture_core_v1.py`
  commit `2ebfe605665232941ae53ec598607a15f6e0f88f`

- synthetic test script:
  `v3/historical_all_market/new_lineage/synthetic_selftest_v1.py`
  commit `dd85b2e0f2c1bc729e9b25ff0b90d90e94aceac7`

- synthetic execution receipt:
  `v3/historical_all_market/governance/NEW_LINEAGE_SYNTHETIC_CORE_SELFTEST_RECEIPT_v1.json`
  commit `916754d745816fdef5044878c7682990ef9483ea`

Synthetic preflight result:
- no real race/result/payout/holdout data used;
- 5 synthetic runners => 60 ordered top-3 states;
- PL and N1 both normalized to approximately 1;
- 3連複 / 2車単 / 2車複 mass approximately 1;
- Wide event-probability mass = 3;
- 2枠単 / 2枠複 mass approximately 1 after synthetic frame aggregation.

This is implementation coherence evidence only, not predictive evidence.

## Additional public benchmark evidence

WINTICKET currently documents that its keirin AI model uses tens of thousands of past race results plus lineup (`並び`) information and exposes a numerical `line power` feature. This should remain external architecture context only unless a future access/use route is separately admitted.

No change to hard boundaries:
- current DEV2000 C new-lineage use prohibited;
- `ECON_HOLDOUT1000 = SEALED`;
- no provider contact/purchase without Owner approval.
