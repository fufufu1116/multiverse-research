from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import historical_virtualworld_nl2_economics_robustness_validation_v2 as engine

base = engine.base
ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_REPLICATION_PREREG_20260913_v4.json'
OUT = ROOT / 'nl2_economics_wide_stability_replication_v4'
OUT.mkdir(parents=True, exist_ok=True)
EXPECTED_NL2_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPECTED_B1A_BLOB = '62ae4ebc17cda47dca1fffae190fa44caae58ca3'
EXPECTED_RULE_SHA256 = 'b73791368ddd93a57751b08d86108a41213e0c71fdcac3f1f2ea4f5039d20284'
FIXED_CONFIG = {
    'configuration_id': 'WIDE:MAX15:P175:AGR140:EV050:FLAT100',
    'profile': 'WIDE_STABILITY',
    'market_group': 'WIDE_ONLY',
    'markets': ['wide'],
    'max_decimal_odds': 15.0,
    'probability_floor': 0.175,
    'max_model_probability_agreement_ratio': 1.4,
    'min_raw_ev': 0.5,
    'min_shape_edge_ratio': 1.5,
}


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if path == RULE and hashlib.sha256(raw).hexdigest() != EXPECTED_RULE_SHA256:
        raise RuntimeError('v4_prereg_file_sha256_mismatch')
    return json.loads(raw.decode('utf-8'))


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def validate_rule(rule: dict) -> None:
    if rule.get('status') != 'PREREGISTERED_BEFORE_V4_REPLICATION_TARGET_ACCESS':
        raise RuntimeError('v4_prereg_status_invalid')
    if rule['probability_models']['primary_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v4_nl2_sha_mismatch')
    if rule['probability_models']['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('v4_b1a_blob_mismatch')
    if rule['probability_models']['probability_coefficient_retune']:
        raise RuntimeError('v4_probability_retune_forbidden')
    gov = rule['governance_inheritance']
    if gov['runtime'] != 'OFF' or gov['automatic_betting'] is not False:
        raise RuntimeError('v4_runtime_or_automatic_betting_invalid')
    if gov['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS':
        raise RuntimeError('v4_econ_holdout_firewall_invalid')
    if gov['DEV2000'] != 'RESULT_PAYOUT_NOT_USED':
        raise RuntimeError('v4_dev2000_firewall_invalid')
    cfg = dict(rule['policy_source']['fixed_configuration'])
    cfg.pop('stake_policy', None); cfg.pop('portfolio_template', None)
    if cfg != FIXED_CONFIG:
        raise RuntimeError('v4_fixed_configuration_mismatch')
    targets = rule['replication_meetings']
    if len(targets) != 10 or len({str(x['meeting_id']) for x in targets}) != 10:
        raise RuntimeError('v4_target_count_or_uniqueness_invalid')
    prior = set(str(x) for x in rule['prior_exposure_snapshot']['meeting_ids'])
    if set(str(x['meeting_id']) for x in targets) & prior:
        raise RuntimeError('v4_target_prior_snapshot_collision')
    if int(rule['prior_exposure_snapshot']['meeting_count']) != len(prior):
        raise RuntimeError('v4_prior_snapshot_count_mismatch')


def collision_audit(rule: dict) -> dict:
    prior_snapshot = set(str(x) for x in rule['prior_exposure_snapshot']['meeting_ids'])
    current_prior, current_sources = base.nl2val.prior_meetings()
    current_prior = set(str(x) for x in current_prior)
    prior = prior_snapshot | current_prior
    targets = {str(x['meeting_id']) for x in rule['replication_meetings']}
    overlap = sorted(targets & prior)
    return {
        'prior_snapshot_count': len(prior_snapshot),
        'current_prior_count': len(current_prior),
        'union_prior_count': len(prior),
        'current_prior_sources': current_sources,
        'target_count': len(targets),
        'target_prior_overlap': overlap,
        'target_prior_overlap_count': len(overlap),
        'ECON_HOLDOUT1000_opened': False,
        'DEV2000_result_or_payout_opened': False,
        'pass': not overlap,
    }


def meeting_block_bootstrap(v: dict, reps: int = 10000, seed: int = 20260914) -> dict:
    meetings = []
    for mid, m in sorted(v['by_meeting'].items()):
        if int(m['stake']) > 0:
            meetings.append((mid, int(m['stake']), int(m['return'])))
    if not meetings:
        return {'valid_replicates': 0, 'lower_2_5': None, 'upper_97_5': None, 'seed': seed, 'replicates_requested': reps}
    rng = random.Random(seed)
    vals = []
    n = len(meetings)
    for _ in range(reps):
        sample = [meetings[rng.randrange(n)] for _ in range(n)]
        stake = sum(x[1] for x in sample)
        ret = sum(x[2] for x in sample)
        if stake > 0:
            vals.append(ret / stake - 1.0)
    vals.sort()
    if not vals:
        return {'valid_replicates': 0, 'lower_2_5': None, 'upper_97_5': None, 'seed': seed, 'replicates_requested': reps}
    def q(p: float) -> float:
        pos = (len(vals)-1)*p
        lo = int(pos); hi = min(lo+1, len(vals)-1); frac = pos-lo
        return vals[lo]*(1-frac)+vals[hi]*frac
    return {
        'valid_replicates': len(vals),
        'lower_2_5': q(0.025),
        'upper_97_5': q(0.975),
        'seed': seed,
        'replicates_requested': reps,
        'meeting_count': n,
    }


def validation_decision(v: dict, selected_count: int, selected_meeting_count: int, rule: dict) -> dict:
    sel = rule['selection_semantics']
    coverage = (
        selected_count >= int(sel['minimum_selected_pre_price_races'])
        and selected_meeting_count == 10
        and v['bet_races'] >= int(sel['minimum_bet_races'])
        and v['executed_tickets'] >= int(sel['minimum_bet_races'])
        and v['wagered_meeting_count'] == 10
        and not v['missing_settlement_races']
    )
    if not coverage:
        return {'status': 'INCONCLUSIVE', 'coverage_pass': False}
    rb = base.bootstrap(v['race_rows'], reps=10000, seed=20260913)
    mb = meeting_block_bootstrap(v, reps=10000, seed=20260914)
    c1 = v['realized_roi'] is not None and v['realized_roi'] > 0
    c2 = v['positive_meeting_count'] >= 6
    c3 = v['maximum_drawdown'] <= 0.20
    c4 = v['largest_single_ticket_return_share'] <= 0.35
    c5 = rb['valid_replicates'] >= 9500 and rb['lower_2_5'] is not None and rb['lower_2_5'] > 0
    c6 = mb['valid_replicates'] >= 9500 and mb['lower_2_5'] is not None and mb['lower_2_5'] > 0
    if all([c1, c2, c3, c4, c5, c6]):
        status = 'PASS_HISTORICAL_ECONOMICS_WIDE_STABILITY_V4_REPLICATION'
    elif all([c1, c2, c3, c4]):
        status = 'POSITIVE_BUT_UNCERTAIN'
    else:
        status = 'FAIL_HISTORICAL_ECONOMICS_WIDE_STABILITY_V4_REPLICATION'
    return {
        'status': status,
        'coverage_pass': True,
        'criteria': {
            'C1_realized_roi_positive': {'pass': c1, 'observed': v['realized_roi']},
            'C2_positive_meetings_at_least_6_of_10': {'pass': c2, 'observed': v['positive_meeting_count']},
            'C3_maximum_drawdown_at_most_0_20': {'pass': c3, 'observed': v['maximum_drawdown']},
            'C4_largest_return_share_at_most_0_35': {'pass': c4, 'observed': v['largest_single_ticket_return_share']},
            'C5_race_bootstrap_lower_bound_positive': {'pass': c5, 'bootstrap': rb},
            'C6_meeting_block_bootstrap_lower_bound_positive': {'pass': c6, 'bootstrap': mb},
        },
    }


def main() -> None:
    rule = load(RULE)
    validate_rule(rule)
    collision = collision_audit(rule)
    dump('00_COLLISION_AND_GOVERNANCE_AUDIT.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V4_COLLISION_AND_GOVERNANCE_AUDIT',
        'preregistration': str(RULE),
        'collision': collision,
        'runtime': 'OFF',
        'automatic_betting': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
    })
    if not collision['pass']:
        raise RuntimeError('v4_replication_collision_gate_fail_closed_' + '_'.join(collision['target_prior_overlap']))

    nl1, nl2 = base.nl2val.load_models()
    if nl2['model_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('v4_loaded_nl2_sha_mismatch')
    base.ticket_choices = engine.ticket_choices

    val, rejected = base.collect_pre_price(rule['replication_meetings'], rule, [FIXED_CONFIG], 'V4_UNTOUCHED_REPLICATION', nl1, nl2)
    counts = dict(sorted(Counter(r['meeting_id'] for r in val).items()))
    dump('01_VALIDATION_DECISION_LOCK.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V4_REPLICATION_DECISION_LOCK',
        'status': 'FROZEN_BEFORE_V4_SETTLEMENT_PARSER_INVOCATION',
        'configuration_id': FIXED_CONFIG['configuration_id'],
        'selected_count': len(val),
        'selected_by_meeting': counts,
        'minimum_required': int(rule['selection_semantics']['minimum_selected_pre_price_races']),
        'settlement_parser_invoked_before_this_lock': False,
        'validation_rejections': rejected,
        'races': val,
    })
    if len(val) < int(rule['selection_semantics']['minimum_selected_pre_price_races']) or len(counts) != 10:
        dump('02_VALIDATION_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V4_REPLICATION_SCORE',
            'decision': {'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE', 'coverage_pass': False},
            'settlement_access': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        return

    settlements, settle_fail = base.fetch_settlements(val)
    if settle_fail:
        dump('02_VALIDATION_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V4_REPLICATION_SCORE',
            'decision': {'status': 'INCONCLUSIVE_SETTLEMENT_FAILURE', 'coverage_pass': False},
            'settlement_failures': settle_fail,
            'runtime': 'OFF',
            'automatic_betting': False,
        })
        return
    v = engine.evaluate_robust(val, settlements, FIXED_CONFIG['configuration_id'])
    decision = validation_decision(v, len(val), len(counts), rule)
    dump('02_VALIDATION_SCORE.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_WIDE_STABILITY_V4_REPLICATION_SCORE',
        'evidence_class': 'FRESH_MEETING_DISJOINT_HISTORICAL_ECONOMICS_KR015',
        'configuration_id': FIXED_CONFIG['configuration_id'],
        'selected_count': len(val),
        'selected_by_meeting': counts,
        'settlement_failures': settle_fail,
        'metrics': v,
        'decision': decision,
        'protected_evidence_firewall': {
            'DEV2000_result_payout_used': False,
            'ECON_HOLDOUT1000_used': False,
            'ECON_HOLDOUT1000_status': 'SEALED',
            'policy_retuned_from_v3_validation': False,
        },
        'runtime': 'OFF',
        'automatic_betting': False,
    })
    print('ECONOMICS_V4_REPLICATION_SUMMARY=' + json.dumps({
        'status': decision['status'],
        'selected_count': len(val),
        'bet_races': v['bet_races'],
        'realized_roi': v['realized_roi'],
        'positive_meeting_count': v['positive_meeting_count'],
        'maximum_drawdown': v['maximum_drawdown'],
        'largest_single_ticket_return_share': v['largest_single_ticket_return_share'],
        'decision': decision,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
