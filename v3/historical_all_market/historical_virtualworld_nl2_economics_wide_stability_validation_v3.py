from __future__ import annotations

import json
from pathlib import Path

import historical_virtualworld_nl2_economics_robustness_validation_v2 as engine

ORIGINAL_COLLISION_AUDIT = engine.collision_audit

ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_DEVELOPMENT_AND_UNTOUCHED_VALIDATION_PREREG_20260913_v3.json'
OUT = ROOT / 'nl2_economics_wide_stability_development_and_untouched_validation_v3'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_NL2_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPECTED_B1A_BLOB = '62ae4ebc17cda47dca1fffae190fa44caae58ca3'
DEV = {
    '2820260822','4820260909','7420260825','8420260909','8720260824',
    '1320260907','2620260906','3720260907','6120260908','7420260909',
}


def _transform(obj):
    if isinstance(obj, dict):
        return {k: _transform(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_transform(v) for v in obj]
    if isinstance(obj, str):
        return (obj
            .replace('KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2', 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V3')
            .replace('V2_DEVELOPMENT', 'V3_DEVELOPMENT')
            .replace('V2_VALIDATION', 'V3_VALIDATION')
            .replace('ROBUSTNESS_V2_UNTOUCHED_VALIDATION', 'WIDE_STABILITY_V3_UNTOUCHED_VALIDATION'))
    return obj


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(
        json.dumps(_transform(obj), ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )


def validate_rule(rule: dict) -> None:
    if rule.get('status') != 'PREREGISTERED_BEFORE_V3_DEVELOPMENT_SETTLEMENT_SCORING':
        raise RuntimeError('v3_prereg_status_invalid')
    if rule['probability_models']['primary_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v3_nl2_sha_mismatch')
    if rule['probability_models']['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('v3_b1a_blob_mismatch')
    if rule['governance_inheritance']['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS':
        raise RuntimeError('econ_holdout_firewall_invalid')
    if rule['governance_inheritance']['DEV2000'] != 'NOT_USED_FOR_V3_SELECTION_OR_VALIDATION':
        raise RuntimeError('dev2000_firewall_invalid')
    f = rule['v2_fresh_target_firewall']
    if f['validation_fetched'] or f['validation_settlement_accessed'] or f['artifact_validation_files_present']:
        raise RuntimeError('v2_fresh_target_firewall_not_clean')
    dev = {str(x['meeting_id']) for x in rule['development_meetings']}
    val = {str(x['meeting_id']) for x in rule['validation_meetings']}
    if dev != DEV:
        raise RuntimeError('v3_development_pool_mismatch')
    if len(val) != 5 or dev & val:
        raise RuntimeError('v3_validation_meeting_count_or_overlap_invalid')
    fam = rule['purchase_policy_family']
    expected = (len(fam['max_decimal_odds_values']) *
                len(fam['probability_floor_values']) *
                len(fam['maximum_model_probability_agreement_ratio_values']) *
                len(fam['minimum_raw_ev_values']))
    if expected != int(fam['configuration_count']) or expected != 64:
        raise RuntimeError('v3_configuration_count_invalid')


def config_space(rule: dict) -> list[dict]:
    fam = rule['purchase_policy_family']
    out = []
    for cap in fam['max_decimal_odds_values']:
        for p_floor in fam['probability_floor_values']:
            for agreement in fam['maximum_model_probability_agreement_ratio_values']:
                for min_ev in fam['minimum_raw_ev_values']:
                    cid = (
                        f"WIDE:MAX{int(float(cap))}:P{int(round(float(p_floor)*1000)):03d}:"
                        f"AGR{int(round(float(agreement)*100)):03d}:EV{int(round(float(min_ev)*100)):03d}:FLAT100"
                    )
                    out.append({
                        'configuration_id': cid,
                        'profile': 'WIDE_STABILITY',
                        'min_raw_ev': float(min_ev),
                        'min_shape_edge_ratio': float(fam['fixed_minimum_shape_edge_ratio']),
                        'market_group': 'WIDE_ONLY',
                        'markets': ['wide'],
                        'max_decimal_odds': float(cap),
                        'probability_floor': float(p_floor),
                        'max_model_probability_agreement_ratio': float(agreement),
                    })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != int(fam['configuration_count']):
        raise RuntimeError('v3_configuration_count_mismatch')
    return out


def dev_select(evals: list[dict]) -> tuple[dict | None, list[dict]]:
    eligible = []
    for x in evals:
        med = x['median_wagered_meeting_roi']
        q1 = x['lower_quartile_wagered_meeting_roi']
        if (
            x['bet_races'] >= 80 and x['executed_tickets'] >= 80 and x['total_stake_jpy'] > 0
            and x['wagered_meeting_count'] == 10 and x['positive_meeting_count'] >= 5
            and x['realized_roi'] is not None and x['realized_roi'] > 0
            and med is not None and med > 0
            and q1 is not None and q1 > -0.75
            and x['maximum_drawdown'] <= 0.20
            and x['largest_single_ticket_return_share'] <= 0.35
            and not x['missing_settlement_races']
        ):
            eligible.append(x)
    eligible.sort(key=lambda x: (
        -x['lower_quartile_wagered_meeting_roi'],
        -x['median_wagered_meeting_roi'],
        -x['positive_meeting_count'],
        x['maximum_drawdown'],
        x['largest_single_ticket_return_share'],
        -x['realized_roi'],
        -x['bet_races'],
        x['configuration_id'],
    ))
    return (eligible[0] if eligible else None), eligible


def validation_decision(v: dict, selected_count: int, meeting_count: int) -> dict:
    coverage = (
        selected_count >= 80 and meeting_count == 5
        and v['bet_races'] >= 30 and v['executed_tickets'] >= 30
        and not v['missing_settlement_races']
    )
    if not coverage:
        return {'status': 'INCONCLUSIVE', 'coverage_pass': False}
    b = engine.base.bootstrap(v['race_rows'], reps=10000, seed=20260913)
    c1 = v['realized_roi'] is not None and v['realized_roi'] > 0
    c2 = v['positive_meeting_count'] >= 3
    c3 = v['maximum_drawdown'] <= 0.20
    c4 = v['largest_single_ticket_return_share'] <= 0.60
    c5 = b['valid_replicates'] >= 9500 and b['lower_2_5'] is not None and b['lower_2_5'] > 0
    if all([c1,c2,c3,c4,c5]):
        status = 'PASS_HISTORICAL_ECONOMICS_WIDE_STABILITY_V3_UNTOUCHED_VALIDATION'
    elif all([c1,c2,c3,c4]):
        status = 'POSITIVE_BUT_UNCERTAIN'
    else:
        status = 'FAIL_HISTORICAL_ECONOMICS_WIDE_STABILITY_V3_UNTOUCHED_VALIDATION'
    return {
        'status': status,
        'coverage_pass': True,
        'criteria': {
            'C1_realized_roi_positive': {'pass': c1, 'observed': v['realized_roi']},
            'C2_positive_meetings_at_least_3_of_5': {'pass': c2, 'observed': v['positive_meeting_count']},
            'C3_maximum_drawdown_at_most_0_20': {'pass': c3, 'observed': v['maximum_drawdown']},
            'C4_largest_return_share_at_most_0_60': {'pass': c4, 'observed': v['largest_single_ticket_return_share']},
            'C5_bootstrap_lower_bound_positive': {'pass': c5, 'bootstrap': b},
        },
    }


def collision_audit(rule: dict) -> dict:
    out = ORIGINAL_COLLISION_AUDIT(rule)
    out['v2_fixed_validation_targets_previously_fetched'] = False
    out['v2_fixed_validation_settlement_previously_accessed'] = False
    out['v2_source_run_id'] = int(rule['v2_fresh_target_firewall']['source_run_id'])
    return out


def main() -> None:
    engine.RULE = RULE
    engine.OUT = OUT
    engine.EXPECTED_NL2_SHA = EXPECTED_NL2_SHA
    engine.EXPECTED_B1A_BLOB = EXPECTED_B1A_BLOB
    engine.validate_rule = validate_rule
    engine.config_space = config_space
    engine.dev_select = dev_select
    engine.validation_decision = validation_decision
    engine.collision_audit = collision_audit
    engine.dump = dump
    engine.main()


if __name__ == '__main__':
    main()
