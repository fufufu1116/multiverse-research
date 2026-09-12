from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import historical_virtualworld_nl2_economics_validation_v1_technical_fix as tech

base = tech.v1

ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_DEVELOPMENT_AND_UNTOUED_VALIDATION_PREREG_20260913_v2.json'
# Corrected immediately below before any execution; kept explicit to make path review fail obvious.
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_DEVELOPMENT_AND_UNTOUCHED_VALIDATION_PREREG_20260913_v2.json'
OUT = ROOT / 'nl2_economics_robustness_development_and_untouched_validation_v2'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_NL2_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPECTED_B1A_BLOB = '62ae4ebc17cda47dca1fffae190fa44caae58ca3'
ECON_V1_DEV = {'2820260822','4820260909','7420260825','8420260909','8720260824'}
ECON_V1_FAILED_VAL = {'1320260907','2620260906','3720260907','6120260908','7420260909'}
CAR_MARKETS = ('3rentan', '2shatan', '3renhuku', '2shahuku', 'wide')


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def validate_rule(rule: dict) -> None:
    if rule.get('status') != 'PREREGISTERED_BEFORE_V2_DEVELOPMENT_SETTLEMENT_SCORING':
        raise RuntimeError('v2_prereg_status_invalid')
    if rule['probability_models']['primary_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v2_nl2_sha_mismatch')
    if rule['probability_models']['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('v2_b1a_blob_mismatch')
    if rule['governance_inheritance']['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS':
        raise RuntimeError('econ_holdout_firewall_invalid')
    if rule['governance_inheritance']['DEV2000'] != 'NOT_USED_FOR_V2_SELECTION_OR_VALIDATION':
        raise RuntimeError('dev2000_firewall_invalid')
    dev = {str(x['meeting_id']) for x in rule['development_meetings']}
    val = {str(x['meeting_id']) for x in rule['validation_meetings']}
    if len(dev) != 10 or len(val) != 5 or dev & val:
        raise RuntimeError('v2_meeting_count_or_overlap_invalid')
    if dev != ECON_V1_DEV | ECON_V1_FAILED_VAL:
        raise RuntimeError('v2_development_pool_not_exactly_exposed_economics_v1_evidence')
    if int(rule['purchase_policy_family']['configuration_count']) != 18:
        raise RuntimeError('v2_configuration_count_rule_invalid')


def collision_audit(rule: dict) -> dict:
    prior, sources = base.nl2val.prior_meetings()
    nl2_audit = load(base.NL2_VALIDATION_AUDIT)
    nl2_val = {str(x['meeting_id']) for x in nl2_audit['selection_integrity']['fixed_meetings']}
    prior |= nl2_val
    sources['nl2_v3_untouched_validation_meetings'] = sorted(nl2_val)
    prior |= ECON_V1_DEV | ECON_V1_FAILED_VAL
    sources['economics_v1_development_meetings'] = sorted(ECON_V1_DEV)
    sources['economics_v1_failed_validation_meetings_consumed'] = sorted(ECON_V1_FAILED_VAL)
    validation = {str(x['meeting_id']) for x in rule['validation_meetings']}
    overlap = sorted(validation & prior)
    date_floor_ok = all(str(x['meeting_id'])[2:] >= '20260901' for x in rule['validation_meetings'])
    return {
        'prior_meeting_count': len(prior),
        'prior_sources': sources,
        'validation_prior_overlap': overlap,
        'validation_prior_overlap_count': len(overlap),
        'validation_all_start_on_or_after_20260901': date_floor_ok,
        'economics_v1_failed_holdout_reused_as_fresh_validation': bool(validation & ECON_V1_FAILED_VAL),
        'dev2000_result_or_payout_opened': False,
        'ECON_HOLDOUT1000_opened': False,
        'pass': not overlap and date_floor_ok,
    }


def config_space(rule: dict) -> list[dict]:
    out = []
    fam = rule['purchase_policy_family']
    for pname, p in fam['profiles'].items():
        for gname, markets in fam['market_groups'].items():
            for cap in fam['max_decimal_odds_values']:
                cap = float(cap)
                out.append({
                    'configuration_id': f'{pname}:{gname}:MAX{int(cap)}:TOP1_TOTAL:FLAT100',
                    'profile': pname,
                    'min_raw_ev': float(p['min_raw_ev']),
                    'min_shape_edge_ratio': float(p['min_shape_edge_ratio']),
                    'market_group': gname,
                    'markets': list(markets),
                    'max_decimal_odds': cap,
                    'probability_floor': float(fam['fixed_probability_floor']),
                    'max_model_probability_agreement_ratio': float(fam['maximum_model_probability_agreement_ratio']),
                })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != int(fam['configuration_count']):
        raise RuntimeError('v2_configuration_count_mismatch')
    return out


def primary_odds(market: str, value) -> float:
    if market == 'wide':
        if not isinstance(value, dict) or 'low' not in value:
            raise RuntimeError('wide_price_missing_low')
        return float(value['low'])
    return float(value)


def ticket_choices(race: dict, price: dict, rule: dict, configs: list[dict]) -> dict[str, list[dict]]:
    active = [int(x) for x in price['active_car_numbers']]
    pre_cars = sorted(int(x['car_no']) for x in race['inputs'])
    if active != pre_cars:
        raise RuntimeError(f'active_car_mismatch_price={active}_pre={pre_cars}')
    sold = [m for m in price['sold_markets'] if m in CAR_MARKETS]
    keys = {m: list(price['closing_price_catalogs'][m].keys()) for m in sold}
    if not sold:
        raise RuntimeError('no_supported_car_markets')

    pn = {int(x['car_no']): float(x['p_win']) for x in race['nl2_ranking']}
    pb = {int(x['car_no']): float(x['p_win']) for x in race['b1a_ranking']}
    if set(pn) != set(active) or set(pb) != set(active):
        raise RuntimeError('prediction_active_car_set_mismatch')
    probs_n, _ = base.pl.build_market_probs(active, pn, sold, keys)
    probs_b, _ = base.pl.build_market_probs(active, pb, sold, keys)

    metrics: dict[str, list[dict]] = defaultdict(list)
    for m in sold:
        cat = price['closing_price_catalogs'][m]
        odds_map = {k: primary_odds(m, v) for k, v in cat.items()}
        if any((not math.isfinite(o) or o <= 0) for o in odds_map.values()):
            raise RuntimeError(f'invalid_market_odds_{m}')
        inv_sum = sum(1.0 / o for o in odds_map.values())
        if not math.isfinite(inv_sum) or inv_sum <= 0:
            raise RuntimeError(f'invalid_market_inv_sum_{m}')
        target_sum = 3.0 if m == 'wide' else 1.0
        for k in sorted(cat):
            o = odds_map[k]
            p_n = float(probs_n[m][k]); p_b = float(probs_b[m][k])
            p_lo = min(p_n, p_b); p_hi = max(p_n, p_b)
            q = (1.0 / o) / inv_sum
            shape_n = (p_n / target_sum) / q
            shape_b = (p_b / target_sum) / q
            metrics[m].append({
                'market': m,
                'ticket': k,
                'primary_odds': o,
                'p_nl2': p_n,
                'p_b1a': p_b,
                'conservative_probability': p_lo,
                'model_probability_agreement_ratio': p_hi / max(p_lo, 1e-15),
                'conservative_raw_ev': min(p_n * o - 1.0, p_b * o - 1.0),
                'conservative_shape_edge_ratio': min(shape_n, shape_b),
            })

    choices: dict[str, list[dict]] = {}
    for c in configs:
        eligible = []
        for m in c['markets']:
            for x in metrics.get(m, []):
                if (x['conservative_probability'] >= c['probability_floor'] and
                    x['primary_odds'] <= c['max_decimal_odds'] and
                    x['conservative_raw_ev'] >= c['min_raw_ev'] and
                    x['conservative_shape_edge_ratio'] >= c['min_shape_edge_ratio'] and
                    x['model_probability_agreement_ratio'] <= c['max_model_probability_agreement_ratio']):
                    eligible.append(x)
        eligible.sort(key=lambda x: (-x['conservative_raw_ev'], -x['conservative_shape_edge_ratio'], -x['conservative_probability'], x['primary_odds'], x['market'], x['ticket']))
        choices[c['configuration_id']] = eligible[:1]
    return choices


def evaluate_robust(races: list[dict], settlements: dict[str, dict], config_id: str) -> dict:
    e = base.evaluate(races, settlements, config_id)
    rois = sorted(float(m['roi']) for m in e['by_meeting'].values() if m['roi'] is not None and m['stake'] > 0)
    e['wagered_meeting_count'] = len(rois)
    e['median_wagered_meeting_roi'] = float(np.median(rois)) if rois else None
    e['lower_quartile_wagered_meeting_roi'] = float(np.percentile(rois, 25, method='linear')) if rois else None
    return e


def dev_select(evals: list[dict]) -> tuple[dict | None, list[dict]]:
    eligible = []
    for x in evals:
        med = x['median_wagered_meeting_roi']
        if (x['bet_races'] >= 60 and x['executed_tickets'] >= 60 and x['total_stake_jpy'] > 0 and
            x['wagered_meeting_count'] >= 8 and x['positive_meeting_count'] >= 5 and
            x['realized_roi'] is not None and x['realized_roi'] > 0 and
            med is not None and med > -0.10 and x['maximum_drawdown'] <= 0.20 and
            x['largest_single_ticket_return_share'] <= 0.35 and not x['missing_settlement_races']):
            eligible.append(x)
    eligible.sort(key=lambda x: (
        -x['median_wagered_meeting_roi'],
        -x['positive_meeting_count'],
        -x['lower_quartile_wagered_meeting_roi'],
        x['maximum_drawdown'],
        x['largest_single_ticket_return_share'],
        -x['realized_roi'],
        -x['bet_races'],
        x['configuration_id'],
    ))
    return (eligible[0] if eligible else None), eligible


def validation_decision(v: dict, selected_count: int, meeting_count: int) -> dict:
    coverage = selected_count >= 80 and meeting_count == 5 and v['bet_races'] >= 30 and v['executed_tickets'] >= 30 and not v['missing_settlement_races']
    if not coverage:
        return {'status': 'INCONCLUSIVE', 'coverage_pass': False}
    b = base.bootstrap(v['race_rows'], reps=10000, seed=20260913)
    c1 = v['realized_roi'] is not None and v['realized_roi'] > 0
    c2 = v['positive_meeting_count'] >= 3
    c3 = v['maximum_drawdown'] <= 0.20
    c4 = v['largest_single_ticket_return_share'] <= 0.60
    c5 = b['valid_replicates'] >= 9500 and b['lower_2_5'] is not None and b['lower_2_5'] > 0
    if all([c1, c2, c3, c4, c5]):
        status = 'PASS_HISTORICAL_ECONOMICS_ROBUSTNESS_V2_UNTOUCHED_VALIDATION'
    elif all([c1, c2, c3, c4]):
        status = 'POSITIVE_BUT_UNCERTAIN'
    else:
        status = 'FAIL_HISTORICAL_ECONOMICS_ROBUSTNESS_V2_UNTOUCHED_VALIDATION'
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


def main() -> None:
    rule = load(RULE)
    validate_rule(rule)
    collision = collision_audit(rule)
    dump('00_COLLISION_AND_GOVERNANCE_AUDIT.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_COLLISION_AND_GOVERNANCE_AUDIT',
        'preregistration': str(RULE),
        'collision': collision,
        'runtime': 'OFF',
        'automatic_betting': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
    })
    if not collision['pass']:
        raise RuntimeError('v2_validation_collision_gate_fail_closed_' + '_'.join(collision['validation_prior_overlap']))

    nl1, nl2 = base.nl2val.load_models()
    if nl2['model_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('loaded_nl2_sha_mismatch')
    configs = config_space(rule)
    base.ticket_choices = ticket_choices

    dev, dev_rejected = base.collect_pre_price(rule['development_meetings'], rule, configs, 'V2_DEVELOPMENT', nl1, nl2)
    dev_counts = dict(sorted(Counter(r['meeting_id'] for r in dev).items()))
    dump('01_DEVELOPMENT_PRE_PRICE_LOCK.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_DEVELOPMENT_PRE_PRICE_LOCK',
        'evidence_class': 'EXPOSED_DEVELOPMENT_ONLY',
        'selected_count': len(dev),
        'selected_by_meeting': dev_counts,
        'minimum_required': int(rule['selection_semantics']['minimum_development_races']),
        'settlement_parser_invoked_before_this_lock': False,
        'historical_price_source_page_may_be_outcome_bearing': True,
        'rejections': dev_rejected,
        'races': dev,
    })
    if len(dev) < int(rule['selection_semantics']['minimum_development_races']) or len(dev_counts) != 10:
        raise RuntimeError('v2_development_pre_price_coverage_fail_closed')

    dev_settle, dev_settle_fail = base.fetch_settlements(dev)
    dev_evals = [evaluate_robust(dev, dev_settle, c['configuration_id']) for c in configs]
    winner, eligible = dev_select(dev_evals)
    dump('02_DEVELOPMENT_SCORE.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_DEVELOPMENT_SCORE',
        'settlement_failures': dev_settle_fail,
        'configuration_count': len(configs),
        'eligible_count': len(eligible),
        'selected_configuration_id': winner['configuration_id'] if winner else None,
        'configurations': dev_evals,
    })
    if dev_settle_fail:
        raise RuntimeError('v2_development_settlement_failure_fail_closed')
    if winner is None:
        dump('03_POLICY_FREEZE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_POLICY_FREEZE',
            'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY',
            'validation_fetched': False,
            'validation_settlement_accessed': False,
        })
        print('ECONOMICS_V2_SUMMARY=' + json.dumps({'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY','development_selected_count':len(dev),'eligible_count':0}, ensure_ascii=False))
        return

    selected_cfg = next(c for c in configs if c['configuration_id'] == winner['configuration_id'])
    freeze = {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_POLICY_FREEZE',
        'status': 'FROZEN_AFTER_V2_DEVELOPMENT_BEFORE_ANY_V2_VALIDATION_TARGET_FETCH',
        'configuration': selected_cfg,
        'portfolio_template': rule['purchase_policy_family']['portfolio_template'],
        'stake_policy': rule['purchase_policy_family']['stake_policy'],
        'development_metrics': {k:winner[k] for k in ['bet_races','executed_tickets','hit_tickets','total_stake_jpy','total_return_jpy','realized_roi','maximum_drawdown','positive_meeting_count','largest_single_ticket_return_share','wagered_meeting_count','median_wagered_meeting_roi','lower_quartile_wagered_meeting_roi']},
        'validation_meetings_already_preregistered': rule['validation_meetings'],
        'validation_target_fetch_before_this_freeze': False,
        'validation_settlement_access_before_this_freeze': False,
        'retune_after_validation': False,
    }
    dump('03_POLICY_FREEZE.json', freeze)

    val, val_rejected = base.collect_pre_price(rule['validation_meetings'], rule, [selected_cfg], 'V2_UNTOUCHED_VALIDATION', nl1, nl2)
    val_counts = dict(sorted(Counter(r['meeting_id'] for r in val).items()))
    dump('04_VALIDATION_DECISION_LOCK.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_UNTOUCHED_VALIDATION_DECISION_LOCK',
        'status': 'FROZEN_BEFORE_V2_VALIDATION_SETTLEMENT_PARSER_INVOCATION',
        'configuration_id': winner['configuration_id'],
        'selected_count': len(val),
        'selected_by_meeting': val_counts,
        'minimum_required': int(rule['selection_semantics']['minimum_validation_races']),
        'settlement_parser_invoked_before_this_lock': False,
        'validation_rejections': val_rejected,
        'races': val,
    })
    if len(val) < int(rule['selection_semantics']['minimum_validation_races']) or len(val_counts) != 5:
        dump('05_VALIDATION_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_UNTOUCHED_VALIDATION_SCORE',
            'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE_NO_VALIDATION_SETTLEMENT_ACCESSED',
            'selected_count': len(val),
            'selected_by_meeting': val_counts,
            'settlement_access': False,
        })
        print('ECONOMICS_V2_SUMMARY=' + json.dumps({'status':'INCONCLUSIVE_PRE_PRICE_COVERAGE','validation_selected_count':len(val),'selected_by_meeting':val_counts}, ensure_ascii=False))
        return

    val_settle, val_settle_fail = base.fetch_settlements(val)
    v = evaluate_robust(val, val_settle, winner['configuration_id'])
    decision = validation_decision(v, len(val), len(val_counts)) if not val_settle_fail else {'status':'INCONCLUSIVE_SETTLEMENT_FAILURE','coverage_pass':False}
    dump('05_VALIDATION_SCORE.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_ROBUSTNESS_V2_UNTOUCHED_VALIDATION_SCORE',
        'evidence_class': 'FRESH_MEETING_DISJOINT_HISTORICAL_ECONOMICS_KR015',
        'configuration_id': winner['configuration_id'],
        'selected_count': len(val),
        'selected_by_meeting': val_counts,
        'settlement_failures': val_settle_fail,
        'metrics': v,
        'decision': decision,
        'protected_evidence_firewall': {
            'DEV2000_result_payout_used': False,
            'DEV2000_segment_c_used': False,
            'ECON_HOLDOUT1000_used': False,
            'ECON_HOLDOUT1000_status': 'SEALED',
            'economics_v1_failed_holdout_used_as_fresh_validation': False,
        },
        'runtime': 'OFF',
        'automatic_betting': False,
    })
    print('ECONOMICS_V2_SUMMARY=' + json.dumps({
        'development_selected_count': len(dev),
        'selected_configuration_id': winner['configuration_id'],
        'development_roi': winner['realized_roi'],
        'development_positive_meetings': winner['positive_meeting_count'],
        'validation_selected_count': len(val),
        'validation_metrics': {k:v[k] for k in ['bet_races','executed_tickets','hit_tickets','total_stake_jpy','total_return_jpy','realized_roi','maximum_drawdown','positive_meeting_count','largest_single_ticket_return_share']},
        'decision': decision,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
