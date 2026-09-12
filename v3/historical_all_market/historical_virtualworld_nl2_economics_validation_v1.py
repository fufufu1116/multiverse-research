from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import historical_virtualworld_new_lineage_stability_untouched_validation_v3 as nl2val
import historical_virtualworld_100_b1a_v1 as b1a
import kdreams_price_catalog_recovery_v1 as price_parser
import kdreams_settlement_recovery_v1 as settlement_parser
import stage1_pl_ticket_probability_engine_v1 as pl

ROOT = Path('v3/historical_all_market/research_candidates')
RULE = ROOT / 'KEIRIN_NL2_ECONOMICS_DEVELOPMENT_AND_UNTOUCHED_VALIDATION_PREREG_20260913_v1.json'
NL2_VALIDATION_AUDIT = ROOT / 'KEIRIN_NEW_LINEAGE_STABILITY_UNTOUCHED_VALIDATION_COMPLETE_AUDIT_20260913_v3.json'
OUT = ROOT / 'nl2_economics_development_and_untouched_validation_v1'
OUT.mkdir(parents=True, exist_ok=True)

CAR_MARKETS = ('3rentan', '2shatan', '3renhuku', '2shahuku', 'wide')
EXPECTED_NL2_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPECTED_B1A_BLOB = '62ae4ebc17cda47dca1fffae190fa44caae58ca3'


def dump(name: str, obj: dict) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def validate_rule(rule: dict) -> None:
    if rule.get('status') != 'PREREGISTERED_BEFORE_NEW_ECONOMIC_SETTLEMENT_SCORING':
        raise RuntimeError('economics_prereg_status_invalid')
    if rule['probability_models']['primary_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('economics_prereg_nl2_sha_mismatch')
    if rule['probability_models']['reference_predictor_blob'] != EXPECTED_B1A_BLOB:
        raise RuntimeError('economics_prereg_b1a_blob_mismatch')
    if rule['governance_inheritance']['ECON_HOLDOUT1000'] != 'SEALED_DO_NOT_ACCESS':
        raise RuntimeError('econ_holdout_firewall_invalid')
    if rule['governance_inheritance']['DEV2000'] != 'NOT_USED_FOR_NEW_ECONOMIC_SELECTION_OR_VALIDATION':
        raise RuntimeError('dev2000_firewall_invalid')
    if len(rule['development_meetings']) != 5 or len(rule['validation_meetings']) != 5:
        raise RuntimeError('meeting_count_invalid')
    dev = {str(x['meeting_id']) for x in rule['development_meetings']}
    val = {str(x['meeting_id']) for x in rule['validation_meetings']}
    if len(dev) != 5 or len(val) != 5 or dev & val:
        raise RuntimeError('meeting_uniqueness_or_overlap_invalid')


def collision_audit(rule: dict) -> dict:
    prior, sources = nl2val.prior_meetings()
    nl2_audit = load(NL2_VALIDATION_AUDIT)
    nl2_val_meetings = {str(x['meeting_id']) for x in nl2_audit['selection_integrity']['fixed_meetings']}
    prior |= nl2_val_meetings
    sources['nl2_v3_untouched_validation_meetings'] = sorted(nl2_val_meetings)
    validation = {str(x['meeting_id']) for x in rule['validation_meetings']}
    overlap = sorted(validation & prior)
    # DEV2000 universe was created 2026-08-15; all fixed validation meetings start in Sep 2026.
    # This date-boundary check avoids opening any DEV2000 RESULT/PAYOUT asset for collision auditing.
    date_floor_ok = all(str(x['meeting_id'])[2:] >= '20260901' for x in rule['validation_meetings'])
    return {
        'prior_meeting_count': len(prior),
        'prior_sources': sources,
        'validation_prior_overlap': overlap,
        'validation_prior_overlap_count': len(overlap),
        'validation_all_start_after_20260901': date_floor_ok,
        'dev2000_universe_created_before_validation_period': True,
        'dev2000_result_or_payout_opened': False,
        'ECON_HOLDOUT1000_opened': False,
        'pass': not overlap and date_floor_ok,
    }


def config_space(rule: dict) -> list[dict]:
    out = []
    for pname, p in rule['purchase_policy_family']['profiles'].items():
        for gname, markets in rule['purchase_policy_family']['market_groups'].items():
            out.append({
                'configuration_id': f'{pname}:{gname}:TOP1_PER_MARKET:FLAT100',
                'profile': pname,
                'min_raw_ev': float(p['min_raw_ev']),
                'min_shape_edge_ratio': float(p['min_shape_edge_ratio']),
                'market_group': gname,
                'markets': list(markets),
            })
    out.sort(key=lambda x: x['configuration_id'])
    if len(out) != int(rule['purchase_policy_family']['configuration_count']):
        raise RuntimeError('configuration_count_mismatch')
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
    probs_n, _ = pl.build_market_probs(active, pn, sold, keys)
    probs_b, _ = pl.build_market_probs(active, pb, sold, keys)

    metrics: dict[str, list[dict]] = defaultdict(list)
    for m in sold:
        cat = price['closing_price_catalogs'][m]
        odds_map = {k: primary_odds(m, v) for k, v in cat.items()}
        inv_sum = sum(1.0 / o for o in odds_map.values())
        if not math.isfinite(inv_sum) or inv_sum <= 0:
            raise RuntimeError(f'invalid_market_inv_sum_{m}')
        target_sum = 3.0 if m == 'wide' else 1.0
        for k in sorted(cat):
            o = odds_map[k]
            p_n = float(probs_n[m][k]); p_b = float(probs_b[m][k])
            q = (1.0 / o) / inv_sum
            shape_n = (p_n / target_sum) / q
            shape_b = (p_b / target_sum) / q
            metrics[m].append({
                'market': m,
                'ticket': k,
                'primary_odds': o,
                'p_nl2': p_n,
                'p_b1a': p_b,
                'conservative_probability': min(p_n, p_b),
                'conservative_raw_ev': min(p_n * o - 1.0, p_b * o - 1.0),
                'conservative_shape_edge_ratio': min(shape_n, shape_b),
            })

    prob_floor = float(rule['purchase_policy_family']['fixed_probability_floor'])
    max_odds = float(rule['purchase_policy_family']['fixed_max_decimal_odds'])
    choices: dict[str, list[dict]] = {}
    for c in configs:
        selected = []
        for m in c['markets']:
            eligible = [x for x in metrics.get(m, []) if
                        x['conservative_probability'] >= prob_floor and
                        x['primary_odds'] <= max_odds and
                        x['conservative_raw_ev'] >= c['min_raw_ev'] and
                        x['conservative_shape_edge_ratio'] >= c['min_shape_edge_ratio']]
            eligible.sort(key=lambda x: (-x['conservative_raw_ev'], -x['conservative_shape_edge_ratio'], -x['conservative_probability'], x['market'], x['ticket']))
            if eligible:
                selected.append(eligible[0])
        choices[c['configuration_id']] = selected
    return choices


def collect_pre_price(targets: list[dict], rule: dict, configs: list[dict], phase: str, nl1: dict, nl2: dict) -> tuple[list[dict], list[dict]]:
    frozen = []
    rejected = []
    for target in targets:
        b1a.CIRC[str(target['venue'])] = float(target['circumference_m'])
        for day in range(1, 5):
            for race_no in range(1, 13):
                try:
                    r = nl2val.freeze_race(target, day, race_no, nl1, nl2)
                    payload = b1a.fetch(r['source_url'])
                    p = price_parser.parse_payload(payload)
                    choices = ticket_choices(r, p, rule, configs)
                    frozen.append({
                        'phase': phase,
                        'race_id': r['race_id'],
                        'source_url': r['source_url'],
                        'meeting_id': r['meeting_id'],
                        'meeting_day_index': r['meeting_day_index'],
                        'race_no': r['race_no'],
                        'venue': r['venue'],
                        'circumference_m': r['circumference_m'],
                        'active_car_numbers': p['active_car_numbers'],
                        'sold_markets': p['sold_markets'],
                        'price_raw_sha256': p['raw_sha256'],
                        'choices_by_configuration': choices,
                    })
                except Exception as e:
                    rejected.append({
                        'phase': phase,
                        'meeting_id': str(target['meeting_id']),
                        'venue': str(target['venue']),
                        'day_index': day,
                        'race_no': race_no,
                        'reason': str(e),
                    })
    frozen.sort(key=lambda x: (x['meeting_id'], x['meeting_day_index'], x['race_no']))
    return frozen, rejected


def fetch_settlements(races: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    out = {}
    failures = []
    for r in races:
        try:
            payload = b1a.fetch(r['source_url'])
            s = settlement_parser.parse_payload(payload)
            out[r['race_id']] = s
        except Exception as e:
            failures.append({'race_id': r['race_id'], 'meeting_id': r['meeting_id'], 'reason': str(e)})
    return out, failures


def evaluate(races: list[dict], settlements: dict[str, dict], config_id: str) -> dict:
    bankroll = 100000
    peak = bankroll
    max_dd = 0.0
    total_stake = total_return = tickets = hits = bet_races = 0
    by_meeting = defaultdict(lambda: {'stake': 0, 'return': 0, 'bet_races': 0, 'tickets': 0, 'hits': 0})
    race_rows = []
    ticket_returns = []
    missing_settlement_races = []
    for r in races:
        selected = list(r['choices_by_configuration'].get(config_id, []))
        if not selected:
            race_rows.append({'race_id': r['race_id'], 'meeting_id': r['meeting_id'], 'stake': 0, 'return': 0, 'tickets': 0, 'hits': 0})
            continue
        if r['race_id'] not in settlements:
            missing_settlement_races.append(r['race_id'])
            continue
        # Flat100; at most one ticket per market. Affordability keeps canonical rank order if ever binding.
        affordable_units = bankroll // 100
        if affordable_units <= 0:
            selected = []
        elif len(selected) > affordable_units:
            selected = selected[:int(affordable_units)]
        stake = 100 * len(selected)
        ret = 0; race_hits = 0
        smap = settlements[r['race_id']]['settlements_yen_per_100']
        for t in selected:
            payout = int(smap.get(t['market'], {}).get(t['ticket'], 0))
            if payout > 0:
                race_hits += 1
                ticket_returns.append(payout)
            ret += payout
        bankroll = bankroll - stake + ret
        if bankroll < 0:
            raise RuntimeError('negative_bankroll_in_flat100_evaluation')
        peak = max(peak, bankroll)
        if peak > 0:
            max_dd = max(max_dd, (peak - bankroll) / peak)
        total_stake += stake; total_return += ret; tickets += len(selected); hits += race_hits
        if selected:
            bet_races += 1
        bm = by_meeting[r['meeting_id']]
        bm['stake'] += stake; bm['return'] += ret; bm['tickets'] += len(selected); bm['hits'] += race_hits
        if selected:
            bm['bet_races'] += 1
        race_rows.append({'race_id': r['race_id'], 'meeting_id': r['meeting_id'], 'stake': stake, 'return': ret, 'tickets': len(selected), 'hits': race_hits})
    meeting_metrics = {}
    for mid, m in sorted(by_meeting.items()):
        meeting_metrics[mid] = {**m, 'roi': (m['return'] / m['stake'] - 1.0) if m['stake'] else None}
    roi = (total_return / total_stake - 1.0) if total_stake else None
    positive_meetings = sum(1 for m in meeting_metrics.values() if m['roi'] is not None and m['roi'] > 0)
    largest_share = (max(ticket_returns) / total_return) if total_return > 0 and ticket_returns else 0.0
    return {
        'configuration_id': config_id,
        'races_with_settlement': len(settlements),
        'missing_settlement_races': missing_settlement_races,
        'bet_races': bet_races,
        'executed_tickets': tickets,
        'hit_tickets': hits,
        'total_stake_jpy': total_stake,
        'total_return_jpy': total_return,
        'realized_roi': roi,
        'ending_bankroll_jpy': bankroll,
        'maximum_drawdown': max_dd,
        'positive_meeting_count': positive_meetings,
        'by_meeting': meeting_metrics,
        'largest_single_ticket_return_share': largest_share,
        'race_rows': race_rows,
    }


def dev_select(evals: list[dict]) -> tuple[dict | None, list[dict]]:
    eligible = [x for x in evals if x['bet_races'] >= 30 and x['executed_tickets'] >= 50 and x['total_stake_jpy'] > 0 and x['ending_bankroll_jpy'] >= 0 and x['maximum_drawdown'] <= 0.25 and not x['missing_settlement_races']]
    eligible.sort(key=lambda x: (-(x['realized_roi'] if x['realized_roi'] is not None else -999), -x['positive_meeting_count'], x['largest_single_ticket_return_share'], x['maximum_drawdown'], -x['bet_races'], x['configuration_id']))
    return (eligible[0] if eligible else None), eligible


def bootstrap(race_rows: list[dict], reps: int = 10000, seed: int = 20260913) -> dict:
    active = [r for r in race_rows if int(r['stake']) > 0]
    if not active:
        return {'valid_replicates': 0, 'omitted_zero_stake': reps, 'lower_2_5': None, 'upper_97_5': None}
    stakes = np.array([float(r['stake']) for r in active], dtype=float)
    returns = np.array([float(r['return']) for r in active], dtype=float)
    rng = np.random.default_rng(seed)
    vals = []
    omitted = 0
    n = len(active)
    for _ in range(reps):
        idx = rng.integers(0, n, size=n)
        s = float(stakes[idx].sum())
        if s <= 0:
            omitted += 1
            continue
        vals.append(float(returns[idx].sum() / s - 1.0))
    if not vals:
        return {'valid_replicates': 0, 'omitted_zero_stake': omitted, 'lower_2_5': None, 'upper_97_5': None}
    return {
        'valid_replicates': len(vals),
        'omitted_zero_stake': omitted,
        'lower_2_5': float(np.percentile(vals, 2.5, method='linear')),
        'upper_97_5': float(np.percentile(vals, 97.5, method='linear')),
        'seed': seed,
        'replicates_requested': reps,
    }


def validation_decision(v: dict, selected_count: int, meeting_count: int) -> dict:
    coverage = selected_count >= 80 and meeting_count == 5 and v['bet_races'] >= 30 and v['executed_tickets'] >= 50 and not v['missing_settlement_races']
    if not coverage:
        return {'status': 'INCONCLUSIVE', 'coverage_pass': False}
    b = bootstrap(v['race_rows'])
    c1 = v['realized_roi'] is not None and v['realized_roi'] > 0
    c2 = v['positive_meeting_count'] >= 3
    c3 = v['maximum_drawdown'] <= 0.20
    c4 = v['largest_single_ticket_return_share'] <= 0.60
    c5 = b['valid_replicates'] >= 9500 and b['lower_2_5'] is not None and b['lower_2_5'] > 0
    if all([c1, c2, c3, c4, c5]):
        status = 'PASS_HISTORICAL_ECONOMICS_UNTOUCHED_VALIDATION'
    elif all([c1, c2, c3, c4]):
        status = 'POSITIVE_BUT_UNCERTAIN'
    else:
        status = 'FAIL_HISTORICAL_ECONOMICS_UNTOUCHED_VALIDATION'
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
        'record': 'KEIRIN_NL2_ECONOMICS_COLLISION_AND_GOVERNANCE_AUDIT_v1',
        'preregistration': str(RULE),
        'collision': collision,
        'runtime': 'OFF',
        'automatic_betting': False,
        'ECON_HOLDOUT1000': 'SEALED_NOT_OPENED',
        'DEV2000_RESULT_PAYOUT': 'NOT_OPENED',
    })
    if not collision['pass']:
        raise RuntimeError('validation_collision_gate_fail_closed_' + '_'.join(collision['validation_prior_overlap']))

    nl1, nl2 = nl2val.load_models()
    if nl2['model_core_sha256'] != EXPECTED_NL2_SHA:
        raise RuntimeError('loaded_nl2_sha_mismatch')
    configs = config_space(rule)

    dev, dev_rejected = collect_pre_price(rule['development_meetings'], rule, configs, 'DEVELOPMENT', nl1, nl2)
    dev_counts = dict(sorted(Counter(r['meeting_id'] for r in dev).items()))
    dump('01_DEVELOPMENT_PRE_PRICE_LOCK.json', {
        'record': 'KEIRIN_NL2_ECONOMICS_DEVELOPMENT_PRE_PRICE_LOCK_v1',
        'evidence_class': 'EXPOSED_DEVELOPMENT_ONLY',
        'selected_count': len(dev),
        'selected_by_meeting': dev_counts,
        'minimum_required': int(rule['selection_semantics']['minimum_development_races']),
        'settlement_parser_invoked_before_this_lock': False,
        'rejections': dev_rejected,
        'races': dev,
    })
    if len(dev) < int(rule['selection_semantics']['minimum_development_races']) or len(dev_counts) != 5:
        raise RuntimeError('development_pre_price_coverage_fail_closed')

    dev_settle, dev_settle_fail = fetch_settlements(dev)
    dev_evals = [evaluate(dev, dev_settle, c['configuration_id']) for c in configs]
    winner, eligible = dev_select(dev_evals)
    dev_report = {
        'record': 'KEIRIN_NL2_ECONOMICS_DEVELOPMENT_SCORE_v1',
        'settlement_failures': dev_settle_fail,
        'configuration_count': len(configs),
        'eligible_count': len(eligible),
        'selected_configuration_id': winner['configuration_id'] if winner else None,
        'configurations': dev_evals,
    }
    dump('02_DEVELOPMENT_SCORE.json', dev_report)
    if dev_settle_fail:
        raise RuntimeError('development_settlement_failure_fail_closed')
    if winner is None:
        dump('03_POLICY_FREEZE.json', {'record': 'KEIRIN_NL2_ECONOMICS_POLICY_FREEZE_v1', 'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY', 'validation_fetched': False})
        print('ECONOMICS_V1_SUMMARY=' + json.dumps({'status': 'NO_DEVELOPMENT_ELIGIBLE_POLICY', 'dev_selected_count': len(dev)}, ensure_ascii=False))
        return

    selected_cfg = next(c for c in configs if c['configuration_id'] == winner['configuration_id'])
    policy_freeze = {
        'record': 'KEIRIN_NL2_ECONOMICS_POLICY_FREEZE_v1',
        'status': 'FROZEN_AFTER_DEVELOPMENT_BEFORE_ANY_VALIDATION_TARGET_FETCH',
        'configuration': selected_cfg,
        'fixed_probability_floor': rule['purchase_policy_family']['fixed_probability_floor'],
        'fixed_max_decimal_odds': rule['purchase_policy_family']['fixed_max_decimal_odds'],
        'portfolio_template': rule['purchase_policy_family']['portfolio_template'],
        'stake_policy': rule['purchase_policy_family']['stake_policy'],
        'development_metrics': {k: winner[k] for k in ['bet_races','executed_tickets','hit_tickets','total_stake_jpy','total_return_jpy','realized_roi','maximum_drawdown','positive_meeting_count','largest_single_ticket_return_share']},
        'validation_meetings_already_preregistered': rule['validation_meetings'],
        'validation_target_fetch_before_this_freeze': False,
        'validation_settlement_access_before_this_freeze': False,
        'retune_after_validation': False,
    }
    dump('03_POLICY_FREEZE.json', policy_freeze)

    # Validation is collected only after the policy freeze above exists. We still compute choices for
    # all 12 configs in-memory through the shared deterministic helper, but only the frozen config is
    # retained below; no alternative validation configuration is scored.
    val_all, val_rejected = collect_pre_price(rule['validation_meetings'], rule, configs, 'UNTOUCHED_VALIDATION', nl1, nl2)
    val = []
    for r in val_all:
        val.append({**r, 'choices_by_configuration': {winner['configuration_id']: r['choices_by_configuration'][winner['configuration_id']]}})
    val_counts = dict(sorted(Counter(r['meeting_id'] for r in val).items()))
    validation_lock = {
        'record': 'KEIRIN_NL2_ECONOMICS_UNTOUCHED_VALIDATION_DECISION_LOCK_v1',
        'status': 'FROZEN_BEFORE_VALIDATION_SETTLEMENT_PARSER_INVOCATION',
        'configuration_id': winner['configuration_id'],
        'selected_count': len(val),
        'selected_by_meeting': val_counts,
        'minimum_required': int(rule['selection_semantics']['minimum_validation_races']),
        'settlement_parser_invoked_before_this_lock': False,
        'validation_rejections': val_rejected,
        'races': val,
    }
    dump('04_VALIDATION_DECISION_LOCK.json', validation_lock)
    if len(val) < int(rule['selection_semantics']['minimum_validation_races']) or len(val_counts) != 5:
        dump('05_VALIDATION_SCORE.json', {
            'record': 'KEIRIN_NL2_ECONOMICS_UNTOUCHED_VALIDATION_SCORE_v1',
            'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE_NO_VALIDATION_SETTLEMENT_ACCESSED',
            'selected_count': len(val),
            'selected_by_meeting': val_counts,
            'settlement_access': False,
        })
        print('ECONOMICS_V1_SUMMARY=' + json.dumps({'status': 'INCONCLUSIVE_PRE_PRICE_COVERAGE', 'validation_selected_count': len(val), 'selected_by_meeting': val_counts}, ensure_ascii=False))
        return

    val_settle, val_settle_fail = fetch_settlements(val)
    v = evaluate(val, val_settle, winner['configuration_id'])
    if val_settle_fail:
        v['settlement_fetch_failures'] = val_settle_fail
    decision = validation_decision(v, len(val), len(val_counts)) if not val_settle_fail else {'status': 'INCONCLUSIVE_SETTLEMENT_FAILURE', 'coverage_pass': False}
    score = {
        'record': 'KEIRIN_NL2_ECONOMICS_UNTOUCHED_VALIDATION_SCORE_v1',
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
        },
        'runtime': 'OFF',
        'automatic_betting': False,
    }
    dump('05_VALIDATION_SCORE.json', score)
    print('ECONOMICS_V1_SUMMARY=' + json.dumps({
        'development_selected_count': len(dev),
        'selected_configuration_id': winner['configuration_id'],
        'development_roi': winner['realized_roi'],
        'validation_selected_count': len(val),
        'validation_metrics': {k: v[k] for k in ['bet_races','executed_tickets','hit_tickets','total_stake_jpy','total_return_jpy','realized_roi','maximum_drawdown','positive_meeting_count','largest_single_ticket_return_share']},
        'decision': decision,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
