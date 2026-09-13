from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

import historical_virtualworld_nl2_economics_robustness_validation_v2 as engine

base = engine.base
ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_DEVELOPMENT_PREREG_20260913_v5.json'
V4_LEDGER = Path('v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v2.jsonl')
OUT = ROOT / 'nl2_economics_cross_meeting_robustness_development_v5'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_RULE_SHA256 = 'c4a28ebb1808399cf3216a536196623f2233b669d2913408b455ef8853138bfc'
EXPECTED_NL2_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPECTED_B1A_BLOB = '62ae4ebc17cda47dca1fffae190fa44caae58ca3'
EXPECTED_V4_LEDGER_COMMIT = '69037223d921e22eae33c9137fa5fedc751c63aa'
EXPECTED_V4_RUN = 34735387522
EXPECTED_V4_ARTIFACT = 10311152397
EXPECTED_POOL = {
    '7420260731','4220260804','1320260806','3520260809','2620260813',
    '2720260814','2820260817','4420260817','2820260822','5520260823',
    '6320260823','8720260824','7420260825','3120260901','6120260902',
    '2820260903','4520260904','6320260904','2620260906','1320260907',
    '3720260907','6120260908','4820260909','7420260909','8420260909',
}
EXPECTED_FOLDS = (
    ('7420260731','2720260814','6320260823','2820260903','3720260907'),
    ('4220260804','2820260817','8720260824','4520260904','6120260908'),
    ('1320260806','4420260817','7420260825','6320260904','4820260909'),
    ('3520260809','2820260822','3120260901','2620260906','7420260909'),
    ('2620260813','5520260823','6120260902','1320260907','8420260909'),
)
EXPECTED_DEVELOPMENT_ELIGIBILITY = {
    'minimum_bet_races': 120,
    'minimum_executed_tickets': 120,
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


def load_json(path: Path) -> dict:
    raw = path.read_bytes()
    if path == RULE and hashlib.sha256(raw).hexdigest() != EXPECTED_RULE_SHA256:
        raise RuntimeError('v5_prereg_file_sha256_mismatch')
    return json.loads(raw.decode('utf-8'))


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )


def load_v4_ledger_record() -> dict:
    found = []
    for line in V4_LEDGER.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get('experiment_id') == 'EXP-NL2-ECONOMICS-WIDE-STABILITY-REPLICATION-V4':
            found.append(row)
    if len(found) != 1:
        raise RuntimeError('v5_v4_canonical_ledger_record_missing_or_duplicate')
    row = found[0]
    if row.get('status') != 'COMPLETE_FAIL':
        raise RuntimeError('v5_v4_canonical_ledger_status_mismatch')
    evidence = row.get('evidence', {})
    if int(evidence.get('run_id', -1)) != EXPECTED_V4_RUN:
        raise RuntimeError('v5_v4_canonical_ledger_run_mismatch')
    if int(evidence.get('artifact_id', -1)) != EXPECTED_V4_ARTIFACT:
        raise RuntimeError('v5_v4_canonical_ledger_artifact_mismatch')
    if row.get('conclusion') != (
        'FAIL_HISTORICAL_ECONOMICS_WIDE_STABILITY_V4_REPLICATION. '
        'Exact V3/V4 policy did not independently replicate and is retired from confirmatory promotion; '
        'same-lineage rescue retuning is prohibited.'
    ):
        raise RuntimeError('v5_v4_canonical_ledger_conclusion_mismatch')
    return row


def validate_rule(rule: dict) -> None:
    if rule.get('record') != 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_DEVELOPMENT_PREREG_20260913_v5':
        raise RuntimeError('v5_prereg_record_invalid')
    if rule.get('status') != 'PREREGISTERED_BEFORE_V5_EXPOSED_DEVELOPMENT_SCORING':
        raise RuntimeError('v5_prereg_status_invalid')
    if rule.get('lineage') != 'NL2_ECONOMICS_V5_CROSS_MEETING_ROBUSTNESS':
        raise RuntimeError('v5_lineage_invalid')
    if rule.get('evidence_class') != 'EXPOSED_DEVELOPMENT_ONLY_NO_FRESH_VALIDATION_ACCESS':
        raise RuntimeError('v5_evidence_class_invalid')

    models = rule['probability_models']
    if models['primary_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v5_nl2_sha_mismatch')
    if models['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('v5_b1a_blob_mismatch')
    if models['probability_coefficient_retune'] is not False:
        raise RuntimeError('v5_probability_retune_forbidden')

    gov = rule['governance_inheritance']
    if gov['runtime'] != 'OFF' or gov['automatic_betting'] is not False or gov['real_money'] is not False:
        raise RuntimeError('v5_live_authority_invalid')
    if gov['fresh_validation_target_access'] is not False:
        raise RuntimeError('v5_fresh_validation_access_forbidden')
    if gov['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS':
        raise RuntimeError('v5_econ_holdout_firewall_invalid')
    if gov['DEV2000'] != 'RESULT_PAYOUT_NOT_USED':
        raise RuntimeError('v5_dev2000_firewall_invalid')
    if gov['same_lineage_v3_v4_retune'] is not False:
        raise RuntimeError('v5_same_lineage_rescue_invalid')

    source = rule['source_evidence']
    if source['canonical_v4_ledger_commit'] != EXPECTED_V4_LEDGER_COMMIT:
        raise RuntimeError('v5_v4_ledger_commit_binding_mismatch')
    if int(source['v4_workflow_run_id']) != EXPECTED_V4_RUN:
        raise RuntimeError('v5_v4_run_binding_mismatch')
    if int(source['v4_artifact_id']) != EXPECTED_V4_ARTIFACT:
        raise RuntimeError('v5_v4_artifact_binding_mismatch')

    pool = rule['development_pool']
    meetings = pool['meetings']
    ids = [str(x['meeting_id']) for x in meetings]
    if int(pool['meeting_count']) != 25 or len(ids) != 25 or len(set(ids)) != 25:
        raise RuntimeError('v5_development_pool_count_or_uniqueness_invalid')
    if set(ids) != EXPECTED_POOL:
        raise RuntimeError('v5_development_pool_identity_mismatch')
    if int(pool['minimum_selected_pre_price_races']) != 600:
        raise RuntimeError('v5_minimum_pre_price_coverage_invalid')
    if pool['all_meetings_required_for_pre_price_coverage'] is not True:
        raise RuntimeError('v5_all_meetings_coverage_rule_invalid')

    folds = rule['cross_meeting_folds']['folds']
    observed_folds = tuple(tuple(str(x) for x in f['meeting_ids']) for f in folds)
    if int(rule['cross_meeting_folds']['fold_count']) != 5 or observed_folds != EXPECTED_FOLDS:
        raise RuntimeError('v5_cross_meeting_fold_definition_mismatch')
    if set(x for fold in observed_folds for x in fold) != EXPECTED_POOL:
        raise RuntimeError('v5_cross_meeting_fold_coverage_mismatch')

    fam = rule['purchase_policy_family']
    if fam['market_group'] != 'WIDE_ONLY' or fam['markets'] != ['wide']:
        raise RuntimeError('v5_market_family_invalid')
    if fam['stake_policy'] != 'FLAT100_JPY_PER_SELECTED_RACE':
        raise RuntimeError('v5_stake_policy_invalid')
    if fam['portfolio_template'] != 'TOP1_TOTAL_PER_RACE_AFTER_FILTERING':
        raise RuntimeError('v5_portfolio_template_invalid')
    expected_count = (
        len(fam['max_decimal_odds_values'])
        * len(fam['probability_floor_values'])
        * len(fam['maximum_model_probability_agreement_ratio_values'])
        * len(fam['minimum_raw_ev_values'])
    )
    if expected_count != 108 or int(fam['configuration_count']) != expected_count:
        raise RuntimeError('v5_configuration_count_invalid')
    if float(fam['fixed_minimum_shape_edge_ratio']) != 1.5:
        raise RuntimeError('v5_shape_edge_rule_invalid')

    if rule['development_eligibility'] != EXPECTED_DEVELOPMENT_ELIGIBILITY:
        raise RuntimeError('v5_development_eligibility_definition_mismatch')


def config_space(rule: dict) -> list[dict]:
    fam = rule['purchase_policy_family']
    out = []
    for cap in fam['max_decimal_odds_values']:
        for p_floor in fam['probability_floor_values']:
            for agreement in fam['maximum_model_probability_agreement_ratio_values']:
                for min_ev in fam['minimum_raw_ev_values']:
                    cid = (
                        f"WIDE:MAX{int(float(cap))}:P{int(round(float(p_floor)*1000)):03d}:"
                        f"AGR{int(round(float(agreement)*100)):03d}:"
                        f"EV{int(round(float(min_ev)*100)):03d}:FLAT100"
                    )
                    out.append({
                        'configuration_id': cid,
                        'profile': 'WIDE_CROSS_MEETING_ROBUSTNESS',
                        'market_group': 'WIDE_ONLY',
                        'markets': ['wide'],
                        'max_decimal_odds': float(cap),
                        'probability_floor': float(p_floor),
                        'max_model_probability_agreement_ratio': float(agreement),
                        'min_raw_ev': float(min_ev),
                        'min_shape_edge_ratio': float(fam['fixed_minimum_shape_edge_ratio']),
                    })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != 108 or len({x['configuration_id'] for x in out}) != 108:
        raise RuntimeError('v5_configuration_space_generation_invalid')
    return out


def fold_metrics(evaluation: dict, rule: dict) -> dict:
    by_meeting = evaluation['by_meeting']
    fold_rows = []
    for f in rule['cross_meeting_folds']['folds']:
        stake = 0
        ret = 0
        wagered = 0
        for mid in f['meeting_ids']:
            m = by_meeting.get(str(mid), {'stake': 0, 'return': 0})
            ms = int(m.get('stake', 0))
            mr = int(m.get('return', 0))
            stake += ms
            ret += mr
            if ms > 0:
                wagered += 1
        roi = (ret / stake - 1.0) if stake > 0 else None
        fold_rows.append({
            'fold': int(f['fold']),
            'meeting_ids': [str(x) for x in f['meeting_ids']],
            'wagered_meetings': wagered,
            'stake_jpy': stake,
            'return_jpy': ret,
            'roi': roi,
        })
    rois = [float(x['roi']) for x in fold_rows if x['roi'] is not None]
    return {
        'folds': fold_rows,
        'all_five_folds_wagered': len(rois) == 5,
        'positive_fold_count': sum(1 for x in rois if x > 0),
        'median_fold_roi': float(statistics.median(rois)) if len(rois) == 5 else None,
        'worst_fold_roi': min(rois) if len(rois) == 5 else None,
    }


def eligibility_flags(e: dict) -> dict:
    flags = {
        'minimum_bet_races': e['bet_races'] >= 120,
        'minimum_executed_tickets': e['executed_tickets'] >= 120,
        'minimum_wagered_meetings': e['wagered_meeting_count'] >= 20,
        'minimum_positive_meetings': e['positive_meeting_count'] >= 12,
        'pooled_roi': e['realized_roi'] is not None and e['realized_roi'] > 0,
        'median_wagered_meeting_roi': (
            e['median_wagered_meeting_roi'] is not None and e['median_wagered_meeting_roi'] > -0.10
        ),
        'lower_quartile_wagered_meeting_roi': (
            e['lower_quartile_wagered_meeting_roi'] is not None
            and e['lower_quartile_wagered_meeting_roi'] > -0.90
        ),
        'maximum_drawdown': e['maximum_drawdown'] <= 0.20,
        'largest_single_ticket_return_share': e['largest_single_ticket_return_share'] <= 0.20,
        'minimum_positive_folds': e['positive_fold_count'] >= 3,
        'median_fold_roi': e['median_fold_roi'] is not None and e['median_fold_roi'] > 0,
        'worst_fold_roi': e['worst_fold_roi'] is not None and e['worst_fold_roi'] > -0.70,
        'all_five_folds_wagered': e['all_five_folds_wagered'] is True,
        'missing_settlement_races': not e['missing_settlement_races'],
    }
    flags['eligible'] = all(flags.values())
    return flags


def selection_key(e: dict) -> tuple:
    return (
        -float(e['worst_fold_roi']),
        -float(e['median_fold_roi']),
        -float(e['median_wagered_meeting_roi']),
        -int(e['positive_meeting_count']),
        float(e['largest_single_ticket_return_share']),
        float(e['maximum_drawdown']),
        -float(e['realized_roi']),
        -int(e['bet_races']),
        str(e['configuration_id']),
    )


def compact_evaluation(e: dict) -> dict:
    return {k: v for k, v in e.items() if k != 'race_rows'}


def main() -> None:
    rule = load_json(RULE)
    validate_rule(rule)
    v4_ledger = load_v4_ledger_record()
    configs = config_space(rule)

    dump('00_GOVERNANCE_AUDIT.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_GOVERNANCE_AUDIT',
        'status': 'PASS_EXPOSED_DEVELOPMENT_ONLY',
        'preregistration': str(RULE),
        'preregistration_sha256': EXPECTED_RULE_SHA256,
        'canonical_v4_ledger': str(V4_LEDGER),
        'canonical_v4_ledger_commit': EXPECTED_V4_LEDGER_COMMIT,
        'canonical_v4_status': v4_ledger['status'],
        'development_meeting_count': 25,
        'development_meeting_ids': sorted(EXPECTED_POOL),
        'configuration_count': len(configs),
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
        'probability_retune': False,
        'runtime': 'OFF',
        'automatic_betting': False,
        'real_money': False,
    })

    nl1, nl2 = base.nl2val.load_models()
    if nl2['model_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v5_loaded_nl2_sha_mismatch')
    base.ticket_choices = engine.ticket_choices

    development, rejected = base.collect_pre_price(
        rule['development_pool']['meetings'],
        rule,
        configs,
        'V5_EXPOSED_DEVELOPMENT',
        nl1,
        nl2,
    )
    counts = dict(sorted(Counter(r['meeting_id'] for r in development).items()))
    dump('01_DEVELOPMENT_PRE_PRICE_LOCK.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_DEVELOPMENT_PRE_PRICE_LOCK',
        'evidence_class': 'EXPOSED_DEVELOPMENT_ONLY',
        'status': 'FROZEN_BEFORE_V5_EXPOSED_DEVELOPMENT_SETTLEMENT_SCORING',
        'selected_count': len(development),
        'selected_by_meeting': counts,
        'minimum_required': int(rule['development_pool']['minimum_selected_pre_price_races']),
        'all_25_meetings_required': True,
        'settlement_parser_invoked_before_this_lock': False,
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
        'rejections': rejected,
        'races': development,
    })

    coverage_ok = (
        len(development) >= int(rule['development_pool']['minimum_selected_pre_price_races'])
        and len(counts) == 25
        and set(counts) == EXPECTED_POOL
    )
    if not coverage_ok:
        dump('02_DEVELOPMENT_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_DEVELOPMENT_SCORE',
            'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE',
            'coverage_pass': False,
            'selected_count': len(development),
            'selected_by_meeting': counts,
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        dump('03_POLICY_FREEZE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_POLICY_FREEZE',
            'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY_COVERAGE_INCONCLUSIVE',
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        print('ECONOMICS_V5_DEVELOPMENT_SUMMARY=' + json.dumps({
            'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE',
            'selected_count': len(development),
            'meeting_count': len(counts),
            'eligible_policy_count': 0,
        }, ensure_ascii=False))
        return

    settlements, settlement_failures = base.fetch_settlements(development)
    if settlement_failures:
        dump('02_DEVELOPMENT_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_DEVELOPMENT_SCORE',
            'status': 'INCONCLUSIVE_SETTLEMENT_FAILURE',
            'coverage_pass': True,
            'settlement_failures': settlement_failures,
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        dump('03_POLICY_FREEZE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_POLICY_FREEZE',
            'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY_SETTLEMENT_INCONCLUSIVE',
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        print('ECONOMICS_V5_DEVELOPMENT_SUMMARY=' + json.dumps({
            'status': 'INCONCLUSIVE_SETTLEMENT_FAILURE',
            'settlement_failure_count': len(settlement_failures),
            'eligible_policy_count': 0,
        }, ensure_ascii=False))
        return

    config_by_id = {x['configuration_id']: x for x in configs}
    evaluations = []
    eligible = []
    for config in configs:
        e = engine.evaluate_robust(development, settlements, config['configuration_id'])
        e.update(fold_metrics(e, rule))
        flags = eligibility_flags(e)
        e['eligibility'] = flags
        evaluations.append(e)
        if flags['eligible']:
            eligible.append(e)

    eligible.sort(key=selection_key)
    winner = eligible[0] if eligible else None

    dump('02_DEVELOPMENT_SCORE.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_DEVELOPMENT_SCORE',
        'status': 'COMPLETE_EXPOSED_DEVELOPMENT_ONLY',
        'coverage_pass': True,
        'selected_count': len(development),
        'selected_by_meeting': counts,
        'configuration_count': len(configs),
        'eligible_policy_count': len(eligible),
        'eligibility_definition': EXPECTED_DEVELOPMENT_ELIGIBILITY,
        'winner_selection_order': rule['winner_selection_order'],
        'configurations': [compact_evaluation(x) for x in evaluations],
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
        'protected_evidence_firewall': {
            'ECON_HOLDOUT1000_used': False,
            'DEV2000_result_payout_used': False,
        },
        'runtime': 'OFF',
        'automatic_betting': False,
    })

    if winner is None:
        freeze = {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_POLICY_FREEZE',
            'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY',
            'configuration_count': len(configs),
            'eligible_policy_count': 0,
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'next_action': 'Stop this lineage before fresh target access. Any successor requires a separately preregistered development design.',
            'runtime': 'OFF',
            'automatic_betting': False,
        }
    else:
        freeze = {
            'record': 'KEIRIN_NL2_ECONOMICS_CROSS_MEETING_ROBUSTNESS_V5_POLICY_FREEZE',
            'status': 'FROZEN_AFTER_EXPOSED_V5_DEVELOPMENT_BEFORE_ANY_FRESH_VALIDATION_PREREG',
            'configuration': config_by_id[winner['configuration_id']],
            'development_metrics': compact_evaluation(winner),
            'eligible_policy_count': len(eligible),
            'fresh_validation_target_selected': False,
            'fresh_validation_target_accessed': False,
            'scientific_claim_boundary': rule['scientific_claim_boundary'],
            'next_action': 'Create a separate preregistration that selects a completely new meeting-disjoint untouched holdout before any fresh PRE/PRICE/RESULT/PAYOUT access.',
            'runtime': 'OFF',
            'automatic_betting': False,
        }
    dump('03_POLICY_FREEZE.json', freeze)

    summary = {
        'status': freeze['status'],
        'selected_count': len(development),
        'meeting_count': len(counts),
        'configuration_count': len(configs),
        'eligible_policy_count': len(eligible),
        'winner': None if winner is None else {
            'configuration_id': winner['configuration_id'],
            'bet_races': winner['bet_races'],
            'hit_tickets': winner['hit_tickets'],
            'executed_tickets': winner['executed_tickets'],
            'realized_roi': winner['realized_roi'],
            'positive_meeting_count': winner['positive_meeting_count'],
            'wagered_meeting_count': winner['wagered_meeting_count'],
            'median_wagered_meeting_roi': winner['median_wagered_meeting_roi'],
            'lower_quartile_wagered_meeting_roi': winner['lower_quartile_wagered_meeting_roi'],
            'positive_fold_count': winner['positive_fold_count'],
            'median_fold_roi': winner['median_fold_roi'],
            'worst_fold_roi': winner['worst_fold_roi'],
            'maximum_drawdown': winner['maximum_drawdown'],
            'largest_single_ticket_return_share': winner['largest_single_ticket_return_share'],
        },
        'fresh_validation_target_selected': False,
        'fresh_validation_target_accessed': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
        'runtime': 'OFF',
        'automatic_betting': False,
    }
    print('ECONOMICS_V5_DEVELOPMENT_SUMMARY=' + json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
