from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import historical_virtualworld_nl2_economics_cross_meeting_robustness_development_v5 as v5

engine = v5.engine
base = v5.base
ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_DIVERSIFIED_WIDE_PORTFOLIO_DEVELOPMENT_PREREG_20260913_v6.json'
LEDGER = Path('v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v2.jsonl')
OUT = ROOT / 'nl2_economics_diversified_wide_portfolio_development_v6'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_RULE_SHA256 = '83c3400f8cccd90e17c8d0934f7981df6da95fa035745c0139bba7f999bc2208'
EXPECTED_NL2_SHA = v5.EXPECTED_NL2_SHA
EXPECTED_B1A_BLOB = v5.EXPECTED_B1A_BLOB
EXPECTED_POOL = v5.EXPECTED_POOL
EXPECTED_FOLDS = v5.EXPECTED_FOLDS
EXPECTED_V5_RUN = 34737854844
EXPECTED_V5_ARTIFACT = 10311983335
EXPECTED_ELIGIBILITY = {
    'minimum_bet_races': 120,
    'minimum_executed_tickets': 200,
    'minimum_wagered_meetings': 20,
    'minimum_positive_meetings': 12,
    'pooled_roi': 'greater_than_0',
    'median_wagered_meeting_roi': 'greater_than_-0.10',
    'lower_quartile_wagered_meeting_roi': 'greater_than_-0.90',
    'maximum_drawdown': 'at_most_0.20',
    'largest_single_ticket_return_share': 'at_most_0.20',
    'minimum_positive_folds': 3,
    'median_fold_roi': 'greater_than_0',
    'worst_fold_roi': 'greater_than_-0.70',
    'all_five_folds_wagered': True,
    'missing_settlement_races': 'none',
}


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load_rule() -> dict:
    raw = RULE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_RULE_SHA256:
        raise RuntimeError('v6_prereg_sha256_mismatch')
    return json.loads(raw.decode('utf-8'))


def load_v5_record() -> dict:
    found = []
    for line in LEDGER.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get('experiment_id') == 'EXP-NL2-ECONOMICS-CROSS-MEETING-ROBUSTNESS-DEVELOPMENT-V5':
                found.append(row)
    if len(found) != 1 or found[0].get('status') != 'COMPLETE_NO_DEVELOPMENT_ELIGIBLE_POLICY':
        raise RuntimeError('v6_v5_ledger_binding_invalid')
    ev = found[0].get('evidence', {})
    if int(ev.get('run_id', -1)) != EXPECTED_V5_RUN or int(ev.get('artifact_id', -1)) != EXPECTED_V5_ARTIFACT:
        raise RuntimeError('v6_v5_evidence_binding_invalid')
    return found[0]


def validate_rule(rule: dict) -> None:
    if rule.get('record') != 'KEIRIN_NL2_ECONOMICS_DIVERSIFIED_WIDE_PORTFOLIO_DEVELOPMENT_PREREG_20260913_v6':
        raise RuntimeError('v6_record_invalid')
    if rule.get('status') != 'PREREGISTERED_BEFORE_V6_EXPOSED_DEVELOPMENT_SCORING':
        raise RuntimeError('v6_status_invalid')
    if rule.get('lineage') != 'NL2_ECONOMICS_V6_DIVERSIFIED_WIDE_PORTFOLIO':
        raise RuntimeError('v6_lineage_invalid')
    if rule.get('evidence_class') != 'EXPOSED_DEVELOPMENT_ONLY_NO_FRESH_VALIDATION_ACCESS':
        raise RuntimeError('v6_evidence_class_invalid')
    models = rule['probability_models']
    if models['primary_core_sha256'] != EXPECTED_NL2_SHA or models['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('v6_model_binding_invalid')
    if models['probability_coefficient_retune'] is not False:
        raise RuntimeError('v6_probability_retune_forbidden')
    gov = rule['governance_inheritance']
    if gov['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS' or gov['DEV2000'] != 'RESULT_PAYOUT_NOT_USED':
        raise RuntimeError('v6_protected_firewall_invalid')
    if gov['fresh_validation_target_access'] is not False or gov['runtime'] != 'OFF' or gov['automatic_betting'] is not False:
        raise RuntimeError('v6_authority_invalid')
    ids = [str(x['meeting_id']) for x in rule['development_pool']['meetings']]
    if len(ids) != 25 or len(set(ids)) != 25 or set(ids) != EXPECTED_POOL:
        raise RuntimeError('v6_pool_invalid')
    folds = tuple(tuple(str(x) for x in f['meeting_ids']) for f in rule['cross_meeting_folds']['folds'])
    if folds != EXPECTED_FOLDS:
        raise RuntimeError('v6_folds_invalid')
    fam = rule['purchase_policy_family']
    expected_count = (
        len(fam['max_tickets_per_race_values'])
        * len(fam['max_decimal_odds_values'])
        * len(fam['probability_floor_values'])
        * len(fam['maximum_model_probability_agreement_ratio_values'])
        * len(fam['minimum_raw_ev_values'])
    )
    if expected_count != 72 or int(fam['configuration_count']) != 72:
        raise RuntimeError('v6_config_count_invalid')
    if rule['development_eligibility'] != EXPECTED_ELIGIBILITY:
        raise RuntimeError('v6_eligibility_invalid')


def config_space(rule: dict) -> list[dict]:
    fam = rule['purchase_policy_family']
    out = []
    for topk in fam['max_tickets_per_race_values']:
        for cap in fam['max_decimal_odds_values']:
            for p_floor in fam['probability_floor_values']:
                for agreement in fam['maximum_model_probability_agreement_ratio_values']:
                    for min_ev in fam['minimum_raw_ev_values']:
                        cid = (
                            f"WIDE:TOP{int(topk)}:MAX{int(float(cap))}:"
                            f"P{int(round(float(p_floor)*1000)):03d}:"
                            f"AGR{int(round(float(agreement)*100)):03d}:"
                            f"EV{int(round(float(min_ev)*100)):03d}:FLAT100"
                        )
                        out.append({
                            'configuration_id': cid,
                            'markets': ['wide'],
                            'max_tickets_per_race': int(topk),
                            'max_decimal_odds': float(cap),
                            'probability_floor': float(p_floor),
                            'max_model_probability_agreement_ratio': float(agreement),
                            'min_raw_ev': float(min_ev),
                            'min_shape_edge_ratio': float(fam['fixed_minimum_shape_edge_ratio']),
                        })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != 72 or len({x['configuration_id'] for x in out}) != 72:
        raise RuntimeError('v6_config_space_generation_invalid')
    return out


def diversified_choices(race: dict, price: dict, rule: dict, configs: list[dict]) -> dict[str, list[dict]]:
    active = [int(x) for x in price['active_car_numbers']]
    pre_cars = sorted(int(x['car_no']) for x in race['inputs'])
    if active != pre_cars:
        raise RuntimeError('v6_active_car_mismatch')
    if 'wide' not in price['sold_markets']:
        return {c['configuration_id']: [] for c in configs}
    cat = price['closing_price_catalogs']['wide']
    odds = {k: engine.primary_odds('wide', v) for k, v in cat.items()}
    inv_sum = sum(1.0 / o for o in odds.values())
    if not math.isfinite(inv_sum) or inv_sum <= 0:
        raise RuntimeError('v6_invalid_wide_price_catalog')
    pn = {int(x['car_no']): float(x['p_win']) for x in race['nl2_ranking']}
    pb = {int(x['car_no']): float(x['p_win']) for x in race['b1a_ranking']}
    probs_n, _ = base.pl.build_market_probs(active, pn, ['wide'], {'wide': list(cat.keys())})
    probs_b, _ = base.pl.build_market_probs(active, pb, ['wide'], {'wide': list(cat.keys())})
    metrics = []
    for k in sorted(cat):
        o = odds[k]
        p_n = float(probs_n['wide'][k]); p_b = float(probs_b['wide'][k])
        p_lo = min(p_n, p_b); p_hi = max(p_n, p_b)
        q = (1.0 / o) / inv_sum
        metrics.append({
            'market': 'wide',
            'ticket': k,
            'primary_odds': o,
            'p_nl2': p_n,
            'p_b1a': p_b,
            'conservative_probability': p_lo,
            'model_probability_agreement_ratio': p_hi / max(p_lo, 1e-15),
            'conservative_raw_ev': min(p_n * o - 1.0, p_b * o - 1.0),
            'conservative_shape_edge_ratio': min((p_n / 3.0) / q, (p_b / 3.0) / q),
        })
    out = {}
    for c in configs:
        eligible = [x for x in metrics if
            x['conservative_probability'] >= c['probability_floor']
            and x['primary_odds'] <= c['max_decimal_odds']
            and x['conservative_raw_ev'] >= c['min_raw_ev']
            and x['conservative_shape_edge_ratio'] >= c['min_shape_edge_ratio']
            and x['model_probability_agreement_ratio'] <= c['max_model_probability_agreement_ratio']]
        eligible.sort(key=lambda x: (-x['conservative_raw_ev'], -x['conservative_shape_edge_ratio'], -x['conservative_probability'], x['primary_odds'], x['ticket']))
        out[c['configuration_id']] = eligible[:c['max_tickets_per_race']]
    return out


def flags(e: dict) -> dict:
    f = {
        'minimum_bet_races': e['bet_races'] >= 120,
        'minimum_executed_tickets': e['executed_tickets'] >= 200,
        'minimum_wagered_meetings': e['wagered_meeting_count'] >= 20,
        'minimum_positive_meetings': e['positive_meeting_count'] >= 12,
        'pooled_roi': e['realized_roi'] is not None and e['realized_roi'] > 0,
        'median_wagered_meeting_roi': e['median_wagered_meeting_roi'] is not None and e['median_wagered_meeting_roi'] > -0.10,
        'lower_quartile_wagered_meeting_roi': e['lower_quartile_wagered_meeting_roi'] is not None and e['lower_quartile_wagered_meeting_roi'] > -0.90,
        'maximum_drawdown': e['maximum_drawdown'] <= 0.20,
        'largest_single_ticket_return_share': e['largest_single_ticket_return_share'] <= 0.20,
        'minimum_positive_folds': e['positive_fold_count'] >= 3,
        'median_fold_roi': e['median_fold_roi'] is not None and e['median_fold_roi'] > 0,
        'worst_fold_roi': e['worst_fold_roi'] is not None and e['worst_fold_roi'] > -0.70,
        'all_five_folds_wagered': e['all_five_folds_wagered'] is True,
        'missing_settlement_races': not e['missing_settlement_races'],
    }
    f['eligible'] = all(f.values())
    return f


def key(e: dict) -> tuple:
    return (
        -float(e['lower_quartile_wagered_meeting_roi']),
        -float(e['worst_fold_roi']),
        -float(e['median_wagered_meeting_roi']),
        -int(e['positive_meeting_count']),
        -float(e['median_fold_roi']),
        float(e['largest_single_ticket_return_share']),
        float(e['maximum_drawdown']),
        -float(e['realized_roi']),
        -int(e['bet_races']),
        str(e['configuration_id']),
    )


def compact(e: dict) -> dict:
    return {k: v for k, v in e.items() if k != 'race_rows'}


def main() -> None:
    rule = load_rule()
    validate_rule(rule)
    v5rec = load_v5_record()
    configs = config_space(rule)
    dump('00_GOVERNANCE_AUDIT.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_V6_GOVERNANCE_AUDIT',
        'status': 'PASS_EXPOSED_DEVELOPMENT_ONLY',
        'preregistration_sha256': EXPECTED_RULE_SHA256,
        'v5_canonical_status': v5rec['status'],
        'development_meeting_count': 25,
        'configuration_count': 72,
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
        'probability_retune': False,
        'runtime': 'OFF',
        'automatic_betting': False,
    })

    nl1, nl2 = base.nl2val.load_models()
    if nl2['model_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v6_loaded_nl2_sha_mismatch')
    base.ticket_choices = diversified_choices
    dev, rejected = base.collect_pre_price(rule['development_pool']['meetings'], rule, configs, 'V6_EXPOSED_DEVELOPMENT', nl1, nl2)
    counts = dict(sorted(Counter(r['meeting_id'] for r in dev).items()))
    dump('01_DEVELOPMENT_PRE_PRICE_LOCK.json', {
        'status': 'FROZEN_BEFORE_V6_EXPOSED_SETTLEMENT_SCORING',
        'selected_count': len(dev),
        'selected_by_meeting': counts,
        'rejections': rejected,
        'races': dev,
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
    })
    if not (len(dev) >= 600 and len(counts) == 25 and set(counts) == EXPECTED_POOL):
        dump('02_DEVELOPMENT_SCORE.json', {'status':'INCONCLUSIVE_PRE_PRICE_COVERAGE','selected_count':len(dev),'eligible_policy_count':0,'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False})
        dump('03_POLICY_FREEZE.json', {'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY_COVERAGE_INCONCLUSIVE','fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,'runtime':'OFF','automatic_betting':False})
        return
    settlements, failures = base.fetch_settlements(dev)
    if failures:
        dump('02_DEVELOPMENT_SCORE.json', {'status':'INCONCLUSIVE_SETTLEMENT_FAILURE','settlement_failures':failures,'eligible_policy_count':0,'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False})
        dump('03_POLICY_FREEZE.json', {'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY_SETTLEMENT_INCONCLUSIVE','fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,'runtime':'OFF','automatic_betting':False})
        return

    evaluations = []
    eligible = []
    by_id = {x['configuration_id']: x for x in configs}
    for c in configs:
        e = engine.evaluate_robust(dev, settlements, c['configuration_id'])
        e.update(v5.fold_metrics(e, rule))
        e['eligibility'] = flags(e)
        evaluations.append(e)
        if e['eligibility']['eligible']:
            eligible.append(e)
    eligible.sort(key=key)
    winner = eligible[0] if eligible else None

    dump('02_DEVELOPMENT_SCORE.json', {
        'record':'KEIRIN_NL2_ECONOMICS_V6_DEVELOPMENT_SCORE',
        'status':'COMPLETE_EXPOSED_DEVELOPMENT_ONLY',
        'coverage_pass':True,
        'selected_count':len(dev),
        'selected_by_meeting':counts,
        'configuration_count':len(configs),
        'eligible_policy_count':len(eligible),
        'eligibility_definition':EXPECTED_ELIGIBILITY,
        'winner_selection_order':rule['winner_selection_order'],
        'configurations':[compact(x) for x in evaluations],
        'fresh_validation_target_selected':False,
        'fresh_validation_target_accessed':False,
        'protected_evidence_firewall':{'ECON_HOLDOUT1000_used':False,'DEV2000_result_payout_used':False},
        'runtime':'OFF',
        'automatic_betting':False,
    })

    if winner is None:
        freeze = {
            'record':'KEIRIN_NL2_ECONOMICS_V6_POLICY_FREEZE',
            'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY',
            'configuration_count':len(configs),
            'eligible_policy_count':0,
            'fresh_validation_target_selected':False,
            'fresh_validation_target_accessed':False,
            'next_action':'Stop V6 before fresh target access. Any successor requires a separately preregistered exposed-only development design.',
            'runtime':'OFF',
            'automatic_betting':False,
        }
    else:
        freeze = {
            'record':'KEIRIN_NL2_ECONOMICS_V6_POLICY_FREEZE',
            'status':'FROZEN_AFTER_EXPOSED_V6_DEVELOPMENT_BEFORE_ANY_FRESH_VALIDATION_PREREG',
            'configuration':by_id[winner['configuration_id']],
            'development_metrics':compact(winner),
            'eligible_policy_count':len(eligible),
            'fresh_validation_target_selected':False,
            'fresh_validation_target_accessed':False,
            'scientific_claim_boundary':rule['scientific_claim_boundary'],
            'next_action':'Create a separate preregistration and zero-collision new meeting-disjoint holdout before any fresh PRE/PRICE/RESULT/PAYOUT access.',
            'runtime':'OFF',
            'automatic_betting':False,
        }
    dump('03_POLICY_FREEZE.json', freeze)
    print('ECONOMICS_V6_DEVELOPMENT_SUMMARY=' + json.dumps({
        'status': freeze['status'],
        'selected_count': len(dev),
        'meeting_count': len(counts),
        'configuration_count': len(configs),
        'eligible_policy_count': len(eligible),
        'winner': None if winner is None else {
            'configuration_id':winner['configuration_id'],
            'bet_races':winner['bet_races'],
            'executed_tickets':winner['executed_tickets'],
            'hit_tickets':winner['hit_tickets'],
            'realized_roi':winner['realized_roi'],
            'positive_meeting_count':winner['positive_meeting_count'],
            'wagered_meeting_count':winner['wagered_meeting_count'],
            'median_wagered_meeting_roi':winner['median_wagered_meeting_roi'],
            'lower_quartile_wagered_meeting_roi':winner['lower_quartile_wagered_meeting_roi'],
            'positive_fold_count':winner['positive_fold_count'],
            'median_fold_roi':winner['median_fold_roi'],
            'worst_fold_roi':winner['worst_fold_roi'],
            'maximum_drawdown':winner['maximum_drawdown'],
            'largest_single_ticket_return_share':winner['largest_single_ticket_return_share'],
        },
        'fresh_validation_target_selected':False,
        'fresh_validation_target_accessed':False,
        'ECON_HOLDOUT1000':'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT':'NOT_OPENED',
        'runtime':'OFF',
        'automatic_betting':False,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
