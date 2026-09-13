from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import historical_virtualworld_nl2_economics_cross_market_coverage_development_v7 as v7

v5 = v7.v5
engine = v7.engine
base = v7.base
ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_FALLBACK_MARKET_ROUTING_DEVELOPMENT_PREREG_20260913_v8.json'
LEDGER = Path('v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v4.jsonl')
OUT = ROOT / 'nl2_economics_fallback_market_routing_development_v8'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_RULE_SHA256 = 'ce936ca88932be96d6387a99fd0d37c6c565d334f71e1a2e15e933c0b3e4bb6a'
EXPECTED_V7_RUN = 34745489816
EXPECTED_V7_ARTIFACT = 10314343274


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load_rule() -> dict:
    raw = RULE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_RULE_SHA256:
        raise RuntimeError('v8_prereg_sha256_mismatch')
    return json.loads(raw.decode('utf-8'))


def load_v7_record() -> dict:
    found = [json.loads(x) for x in LEDGER.read_text(encoding='utf-8').splitlines()
             if x.strip() and json.loads(x).get('experiment_id') == 'EXP-NL2-ECONOMICS-CROSS-MARKET-COVERAGE-DEVELOPMENT-V7']
    if len(found) != 1 or found[0].get('status') != 'COMPLETE_NO_DEVELOPMENT_ELIGIBLE_POLICY':
        raise RuntimeError('v8_v7_ledger_binding_invalid')
    ev = found[0].get('evidence', {})
    if int(ev.get('run_id', -1)) != EXPECTED_V7_RUN or int(ev.get('artifact_id', -1)) != EXPECTED_V7_ARTIFACT:
        raise RuntimeError('v8_v7_evidence_binding_invalid')
    return found[0]


def validate_rule(rule: dict) -> None:
    if rule.get('record') != 'KEIRIN_NL2_ECONOMICS_FALLBACK_MARKET_ROUTING_DEVELOPMENT_PREREG_20260913_v8':
        raise RuntimeError('v8_record_invalid')
    if rule.get('status') != 'PREREGISTERED_BEFORE_V8_EXPOSED_DEVELOPMENT_SCORING':
        raise RuntimeError('v8_status_invalid')
    if rule.get('lineage') != 'NL2_ECONOMICS_V8_FALLBACK_MARKET_ROUTING':
        raise RuntimeError('v8_lineage_invalid')
    if rule.get('evidence_class') != 'EXPOSED_DEVELOPMENT_ONLY_NO_FRESH_VALIDATION_ACCESS':
        raise RuntimeError('v8_evidence_class_invalid')
    models = rule['probability_models']
    if models['primary_core_sha256'] != v7.EXPECTED_NL2_SHA or models['reference_predictor_blob'] != v7.EXPECTED_B1A_BLOB:
        raise RuntimeError('v8_model_binding_invalid')
    if models['probability_coefficient_retune'] is not False:
        raise RuntimeError('v8_probability_retune_forbidden')
    gov = rule['governance_inheritance']
    if gov['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS' or gov['DEV2000'] != 'RESULT_PAYOUT_NOT_USED':
        raise RuntimeError('v8_protected_firewall_invalid')
    if gov['fresh_validation_target_access'] is not False or gov['runtime'] != 'OFF' or gov['automatic_betting'] is not False:
        raise RuntimeError('v8_authority_invalid')
    ids = [str(x['meeting_id']) for x in rule['development_pool']['meetings']]
    if len(ids) != 25 or len(set(ids)) != 25 or set(ids) != v7.EXPECTED_POOL:
        raise RuntimeError('v8_pool_invalid')
    folds = tuple(tuple(str(x) for x in f['meeting_ids']) for f in rule['cross_meeting_folds']['folds'])
    if folds != v7.EXPECTED_FOLDS:
        raise RuntimeError('v8_folds_invalid')
    fam = rule['fallback_policy_family']
    count = (len(fam['fallback_markets']) * len(fam['max_decimal_odds_values']) *
             len(fam['probability_floor_values']) * len(fam['maximum_model_probability_agreement_ratio_values']) *
             len(fam['minimum_raw_ev_values']))
    if count != 72 or int(fam['configuration_count']) != 72:
        raise RuntimeError('v8_config_count_invalid')
    if rule['development_eligibility'] != v7.EXPECTED_ELIGIBILITY:
        raise RuntimeError('v8_eligibility_invalid')


def config_space(rule: dict) -> list[dict]:
    fam = rule['fallback_policy_family']
    out = []
    for fallback in fam['fallback_markets']:
        for cap in fam['max_decimal_odds_values']:
            for p_floor in fam['probability_floor_values']:
                for agreement in fam['maximum_model_probability_agreement_ratio_values']:
                    for min_ev in fam['minimum_raw_ev_values']:
                        cid = (f"ROUTE:WIDE>{str(fallback).upper()}:MAX{int(float(cap))}:"
                               f"P{int(round(float(p_floor)*1000)):03d}:"
                               f"AGR{int(round(float(agreement)*100)):03d}:"
                               f"EV{int(round(float(min_ev)*100)):03d}:FLAT100")
                        out.append({
                            'configuration_id': cid,
                            'markets': ['wide', str(fallback)],
                            'primary_market': 'wide',
                            'fallback_market': str(fallback),
                            'max_decimal_odds': float(cap),
                            'probability_floor': float(p_floor),
                            'max_model_probability_agreement_ratio': float(agreement),
                            'min_raw_ev': float(min_ev),
                            'min_shape_edge_ratio': float(fam['fixed_minimum_shape_edge_ratio']),
                        })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != 72 or len({x['configuration_id'] for x in out}) != 72:
        raise RuntimeError('v8_config_space_generation_invalid')
    return out


def fallback_choices(race: dict, price: dict, rule: dict, configs: list[dict]) -> dict[str, list[dict]]:
    expanded = []
    for c in configs:
        primary = dict(c)
        primary['configuration_id'] = c['configuration_id'] + '::PRIMARY'
        primary['markets'] = ['wide']
        fallback = dict(c)
        fallback['configuration_id'] = c['configuration_id'] + '::FALLBACK'
        fallback['markets'] = [c['fallback_market']]
        expanded.extend([primary, fallback])
    independent = v7.cross_market_choices(race, price, rule, expanded)
    out = {}
    for c in configs:
        wide = independent[c['configuration_id'] + '::PRIMARY']
        fallback = independent[c['configuration_id'] + '::FALLBACK']
        if len(wide) > 1 or len(fallback) > 1:
            raise RuntimeError('v8_market_pick_cardinality_invalid')
        chosen = wide[:1] if wide else fallback[:1]
        if len(chosen) > 1:
            raise RuntimeError('v8_more_than_one_ticket_selected')
        out[c['configuration_id']] = chosen
    return out


def compact(e: dict) -> dict:
    return {k: v for k, v in e.items() if k != 'race_rows'}


def main() -> None:
    rule = load_rule()
    validate_rule(rule)
    v7rec = load_v7_record()
    configs = config_space(rule)

    dump('00_GOVERNANCE_AUDIT.json', {
        'record':'KEIRIN_NL2_ECONOMICS_V8_GOVERNANCE_AUDIT',
        'status':'PASS_EXPOSED_DEVELOPMENT_ONLY',
        'preregistration_sha256':EXPECTED_RULE_SHA256,
        'v7_canonical_status':v7rec['status'],
        'development_meeting_count':25,
        'configuration_count':72,
        'routing':'AT_MOST_ONE_TICKET_PER_RACE_PRIMARY_WIDE_ELSE_FALLBACK',
        'fresh_validation_target_selected':False,
        'fresh_validation_target_accessed':False,
        'ECON_HOLDOUT1000':'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT':'NOT_OPENED',
        'probability_retune':False,
        'runtime':'OFF',
        'automatic_betting':False,
    })

    nl1, nl2 = base.nl2val.load_models()
    if nl2['model_core_sha256'] != v7.EXPECTED_NL2_SHA:
        raise RuntimeError('v8_loaded_nl2_sha_mismatch')
    base.ticket_choices = fallback_choices
    dev, rejected = base.collect_pre_price(rule['development_pool']['meetings'], rule, configs, 'V8_EXPOSED_DEVELOPMENT', nl1, nl2)
    counts = dict(sorted(Counter(r['meeting_id'] for r in dev).items()))
    violations = [{'race_id':r['race_id'],'configuration_id':cid,'ticket_count':len(ch)}
                  for r in dev for cid, ch in r['choices_by_configuration'].items() if len(ch) > 1]
    if violations:
        raise RuntimeError('v8_one_ticket_routing_violation')

    dump('01_DEVELOPMENT_PRE_PRICE_LOCK.json', {
        'status':'FROZEN_BEFORE_V8_EXPOSED_SETTLEMENT_SCORING',
        'selected_count':len(dev),'selected_by_meeting':counts,'rejections':rejected,'races':dev,
        'one_ticket_routing_violations':violations,
        'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,
    })

    if not (len(dev) >= 600 and len(counts) == 25 and set(counts) == v7.EXPECTED_POOL):
        dump('02_DEVELOPMENT_SCORE.json', {'status':'INCONCLUSIVE_PRE_PRICE_COVERAGE','selected_count':len(dev),'eligible_policy_count':0,'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False})
        dump('03_POLICY_FREEZE.json', {'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY_COVERAGE_INCONCLUSIVE','fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,'runtime':'OFF','automatic_betting':False})
        return

    settlements, failures = base.fetch_settlements(dev)
    if failures:
        dump('02_DEVELOPMENT_SCORE.json', {'status':'INCONCLUSIVE_SETTLEMENT_FAILURE','settlement_failures':failures,'eligible_policy_count':0,'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False})
        dump('03_POLICY_FREEZE.json', {'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY_SETTLEMENT_INCONCLUSIVE','fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,'runtime':'OFF','automatic_betting':False})
        return

    evaluations, eligible = [], []
    by_id = {x['configuration_id']: x for x in configs}
    for c in configs:
        e = engine.evaluate_robust(dev, settlements, c['configuration_id'])
        e.update(v5.fold_metrics(e, rule))
        e['eligibility'] = v7.flags(e)
        evaluations.append(e)
        if e['eligibility']['eligible']:
            eligible.append(e)
    eligible.sort(key=v7.key)
    winner = eligible[0] if eligible else None

    dump('02_DEVELOPMENT_SCORE.json', {
        'record':'KEIRIN_NL2_ECONOMICS_V8_DEVELOPMENT_SCORE','status':'COMPLETE_EXPOSED_DEVELOPMENT_ONLY',
        'coverage_pass':True,'selected_count':len(dev),'selected_by_meeting':counts,
        'configuration_count':len(configs),'eligible_policy_count':len(eligible),
        'eligibility_definition':v7.EXPECTED_ELIGIBILITY,'winner_selection_order':rule['winner_selection_order'],
        'configurations':[compact(x) for x in evaluations],
        'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,
        'protected_evidence_firewall':{'ECON_HOLDOUT1000_used':False,'DEV2000_result_payout_used':False},
        'runtime':'OFF','automatic_betting':False,
    })

    freeze = {
        'record':'KEIRIN_NL2_ECONOMICS_V8_POLICY_FREEZE',
        'status':'NO_DEVELOPMENT_ELIGIBLE_POLICY' if winner is None else 'FROZEN_AFTER_EXPOSED_V8_DEVELOPMENT_BEFORE_ANY_FRESH_VALIDATION_PREREG',
        'configuration_count':len(configs),'eligible_policy_count':len(eligible),
        'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,
        'runtime':'OFF','automatic_betting':False,
    }
    if winner is not None:
        freeze['configuration'] = by_id[winner['configuration_id']]
        freeze['development_metrics'] = compact(winner)
        freeze['scientific_claim_boundary'] = rule['scientific_claim_boundary']
    dump('03_POLICY_FREEZE.json', freeze)

    print('ECONOMICS_V8_DEVELOPMENT_SUMMARY=' + json.dumps({
        'status':freeze['status'],'selected_count':len(dev),'meeting_count':len(counts),
        'configuration_count':len(configs),'eligible_policy_count':len(eligible),
        'winner':None if winner is None else compact(winner),
        'fresh_validation_target_selected':False,'fresh_validation_target_accessed':False,
        'ECON_HOLDOUT1000':'SEALED_NOT_OPENED','DEV2000_RESULT_PAYOUT':'NOT_OPENED',
        'runtime':'OFF','automatic_betting':False,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
