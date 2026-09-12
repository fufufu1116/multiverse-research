from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # noqa: F401; installs hardened result parser

v1.CIRC.update({
    'maebashi': 335.0,
    'kawasaki': 400.0,
    'utsunomiya': 500.0,
})

SEED = Path('.github/workflows/races.csv')
BATCH3_AUDIT = Path('v3/historical_all_market/research_candidates/KEIRIN_INDEPENDENT_MEETING_REPLICATION_100_B1A_COMPLETE_AUDIT_20260913_v1.json')
BATCH4_AUDIT = Path('v3/historical_all_market/research_candidates/KEIRIN_COVERAGE_BALANCED_INDEPENDENT_MEETING_100_B1A_COMPLETE_AUDIT_20260913_v2.json')
BATCH5_AUDIT = Path('v3/historical_all_market/research_candidates/KEIRIN_REGIME_VALIDATION_FIXED_MEETINGS_B1A_COMPLETE_AUDIT_20260913_v1.json')
SELECTION_RULE = Path('v3/historical_all_market/research_candidates/KEIRIN_REGIME_SIGNAL_CONFIRMATION_FIXED_MEETINGS_SELECTION_RULE_20260913_v1.json')
OUT = Path('v3/historical_all_market/research_candidates/virtualworld_regime_signal_confirmation_fixed_meetings_b1a_v1')
OUT.mkdir(parents=True, exist_ok=True)

FIXED = [
    {'meeting_id': '2220260722', 'venue': 'maebashi', 'circ': 335.0},
    {'meeting_id': '2420260806', 'venue': 'utsunomiya', 'circ': 500.0},
    {'meeting_id': '7520260831', 'venue': 'matsuyama', 'circ': 400.0},
    {'meeting_id': '8420260903', 'venue': 'takeo', 'circ': 400.0},
    {'meeting_id': '3420260910', 'venue': 'kawasaki', 'circ': 400.0},
    {'meeting_id': '4620260910', 'venue': 'toyama', 'circ': 333.3},
]

EXPLICIT_SMALL_EXCLUDED = {
    '2220260809', '2220260815', '2220260912',
    '2520260427', '2520260522', '2520260701',
    '2420260521', '7420260629',
}


def meeting_from_url(url: str) -> str:
    p = urlparse(url).path.strip('/').split('/')
    return p[-4]


def prior_meetings() -> set[str]:
    required = [SEED, BATCH3_AUDIT, BATCH4_AUDIT, BATCH5_AUDIT, SELECTION_RULE]
    if any(not p.exists() for p in required):
        missing = [str(p) for p in required if not p.exists()]
        raise RuntimeError('required_prior_collision_artifact_missing_fail_closed_' + '_'.join(missing))

    prior = {meeting_from_url(x['url']) for x in csv.DictReader(SEED.read_text(encoding='utf-8').splitlines())}

    b3 = json.loads(BATCH3_AUDIT.read_text(encoding='utf-8'))
    prior.update(str(x['meeting_id']) for x in b3['selection']['selected_meetings'])

    b4 = json.loads(BATCH4_AUDIT.read_text(encoding='utf-8'))
    for meetings in b4['selection']['selected_unique_meetings_by_venue'].values():
        prior.update(str(x) for x in meetings)

    b5 = json.loads(BATCH5_AUDIT.read_text(encoding='utf-8'))
    prior.update(str(x) for x in b5['key_preregistered_slices']['meeting'].keys())

    prior.update(EXPLICIT_SMALL_EXCLUDED)
    return prior


def race_url(meeting: str, di: str, rr: int) -> str:
    day = f'{meeting}{di}00'
    return f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{rr:02d}/3rentan/'


def entropy_norm(ranking: list[dict]) -> float:
    p = np.array([float(x['p_win']) for x in ranking], dtype=float)
    h = -float(np.sum(p * np.log(np.maximum(p, 1e-15))))
    return h / math.log(len(p)) if len(p) > 1 else 0.0


def entropy_bin(x: float) -> str:
    if x < 0.70:
        return '[0,0.70)'
    if x < 0.85:
        return '[0.70,0.85)'
    return '[0.85,1.0000001]'


def margin_bin(x: float) -> str:
    if x < 0.05:
        return '[0,0.05)'
    if x < 0.15:
        return '[0.05,0.15)'
    return '[0.15,1.0]'


def class_coarse(rows: list[dict]) -> str:
    classes = [str(r['class']) for r in rows]
    if all(x == 'L1' for x in classes):
        return 'ALL_L1'
    if any(x in {'SS', 'S1', 'S2'} for x in classes):
        return 'CONTAINS_S'
    if all(x in {'A1', 'A2', 'A3'} for x in classes):
        return 'A_ONLY'
    return 'MIXED_OTHER'


def style_signature(rows: list[dict]) -> str:
    c = Counter(str(r['style']) for r in rows)
    return f"逃{c.get('逃',0)}|追{c.get('追',0)}|両{c.get('両',0)}"


def freeze_regime(meeting: str, venue: str, di: str, rr: int, circ_expected: float) -> dict:
    rid = f'REGCONF1_{meeting}_{venue}_{di}_{rr:02d}R'
    url = race_url(meeting, di, rr)
    payload = v1.fetch(url)
    rows, parsed_venue, circ = v1.parse_pre(rid, url, payload)
    if parsed_venue != venue:
        raise RuntimeError(f'venue_mismatch_{parsed_venue}_{venue}')
    if abs(float(circ) - float(circ_expected)) > 1e-9:
        raise RuntimeError(f'circumference_mismatch_{circ}_{circ_expected}')

    ranking = v1.predict(rows)
    probs = [float(x['p_win']) for x in ranking]
    score_values = np.array([float(r['score']) for r in rows], dtype=float)
    class_counts = Counter(str(r['class']) for r in rows)
    style_counts = Counter(str(r['style']) for r in rows)

    return {
        'race_id': rid,
        'source_url': url,
        'meeting_id': meeting,
        'meeting_day_index': int(di),
        'race_no': rr,
        'venue': venue,
        'circumference_m': float(circ),
        'inputs': rows,
        'ranking': ranking,
        'regime': {
            'field_size': len(rows),
            'class_counts': dict(sorted(class_counts.items())),
            'class_coarse': class_coarse(rows),
            'style_counts': dict(sorted(style_counts.items())),
            'style_signature': style_signature(rows),
            'score_population_sd': float(score_values.std()),
            'score_range': float(score_values.max() - score_values.min()),
            'B_mean': float(np.mean([float(r['B']) for r in rows])),
            'S_mean': float(np.mean([float(r['S']) for r in rows])),
            'model_normalized_entropy': entropy_norm(ranking),
            'model_normalized_entropy_bin': entropy_bin(entropy_norm(ranking)),
            'model_top1_margin': float(probs[0] - probs[1]) if len(probs) > 1 else 1.0,
            'model_top1_margin_bin': margin_bin(float(probs[0] - probs[1]) if len(probs) > 1 else 1.0),
        },
    }


def metric(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        'n': n,
        'top1_hits': sum(bool(x['top1_hit']) for x in rows),
        'top1_accuracy': sum(bool(x['top1_hit']) for x in rows) / n if n else None,
        'winner_top3': sum(bool(x['top3_hit']) for x in rows),
        'top3_rate': sum(bool(x['top3_hit']) for x in rows) / n if n else None,
        'mean_log_loss': sum(float(x['log_loss']) for x in rows) / n if n else None,
    }


def grouped(scored: list[dict], key_fn) -> dict:
    keys = sorted({str(key_fn(x)) for x in scored})
    return {k: metric([x for x in scored if str(key_fn(x)) == k]) for k in keys}


def confirmation_decisions(by_entropy: dict, by_day: dict) -> dict:
    low = by_entropy.get('[0,0.70)')
    high = by_entropy.get('[0.85,1.0000001]')
    if not low or int(low['n']) < 10 or not high:
        entropy_status = 'INCONCLUSIVE_INSUFFICIENT_CELL'
    elif float(low['top1_accuracy']) > float(high['top1_accuracy']):
        entropy_status = 'PASS_DIRECTIONAL_REPLICATION'
    else:
        entropy_status = 'FAIL_DIRECTIONAL_REPLICATION'

    d1 = by_day.get('1')
    d2 = by_day.get('2')
    d3 = by_day.get('3')
    if not d1 or not d2 or not d3:
        day_status = 'INCONCLUSIVE_MISSING_DAY_CELL'
    elif float(d2['top1_accuracy']) > float(d1['top1_accuracy']) and float(d2['top1_accuracy']) > float(d3['top1_accuracy']):
        day_status = 'PASS_DIRECTIONAL_REPLICATION'
    else:
        day_status = 'FAIL_DIRECTIONAL_REPLICATION'

    return {
        'H1_NORMALIZED_ENTROPY_DIRECTION': {
            'status': entropy_status,
            'low_entropy': low,
            'high_entropy': high,
            'criterion': 'low entropy Top1 > high entropy Top1 with low-entropy n>=10',
        },
        'H2_MEETING_DAY2_DIRECTION': {
            'status': day_status,
            'day1': d1,
            'day2': d2,
            'day3': d3,
            'criterion': 'day2 Top1 > both day1 and day3 Top1',
        },
        'H3_TOP1_MARGIN_FALSIFICATION_CONTROL': {
            'status': 'REPORTED_NO_MONOTONICITY_ASSUMPTION',
        },
    }


def main() -> None:
    prior = prior_meetings()
    fixed_ids = {x['meeting_id'] for x in FIXED}
    overlap = sorted(fixed_ids & prior)
    if overlap:
        raise RuntimeError('fixed_prior_meeting_overlap_' + '_'.join(overlap))

    frozen: list[dict] = []
    rejected: list[dict] = []
    for target in FIXED:
        meeting = target['meeting_id']
        venue = target['venue']
        for di in ('01', '02', '03', '04'):
            for rr in range(1, 13):
                try:
                    frozen.append(freeze_regime(meeting, venue, di, rr, float(target['circ'])))
                except Exception as e:
                    rejected.append({
                        'meeting_id': meeting,
                        'venue': venue,
                        'day_index': di,
                        'race_no': rr,
                        'reason': str(e),
                    })

    selected_meetings = sorted({x['meeting_id'] for x in frozen})
    selection_audit = {
        'record': 'KEIRIN_REGIME_SIGNAL_CONFIRMATION_FIXED_MEETINGS_SELECTION_EXECUTION_v1',
        'result_access_during_selection': False,
        'payout_access_during_selection': False,
        'odds_used': False,
        'fixed_meeting_ids': [x['meeting_id'] for x in FIXED],
        'prior_meeting_exclusion_count': len(prior),
        'prior_meeting_overlap_count': 0,
        'candidate_count': len(FIXED) * 4 * 12,
        'selected_count': len(frozen),
        'selected_unique_meeting_count': len(selected_meetings),
        'selected_meetings': selected_meetings,
        'selected_by_meeting': dict(sorted(Counter(x['meeting_id'] for x in frozen).items())),
        'selected_by_venue': dict(sorted(Counter(x['venue'] for x in frozen).items())),
        'selected_by_exact_circumference': dict(sorted(Counter(str(x['circumference_m']) for x in frozen).items())),
        'selected_by_field_size': dict(sorted(Counter(str(x['regime']['field_size']) for x in frozen).items())),
        'selection_order': 'fixed meeting order; day 01/02/03/04 asc; race 01..12 asc; retain every mandatory-PRE-complete candidate',
        'rejected_pre_only': rejected,
    }
    (OUT / 'SELECTION_AUDIT.json').write_text(json.dumps(selection_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if len(frozen) < 120:
        raise RuntimeError(f'regime_confirmation_selected_{len(frozen)}_below_preregistered_minimum_120')
    if len(selected_meetings) < 5:
        raise RuntimeError(f'regime_confirmation_meetings_{len(selected_meetings)}_below_preregistered_minimum_5')

    lock = {
        'record': 'KEIRIN_REGIME_SIGNAL_CONFIRMATION_FIXED_MEETINGS_B1A_PREDICTION_LOCK_v1',
        'evidence_class': 'RETROSPECTIVE_KR015_REGIME_SIGNAL_CONFIRMATION',
        'model': v1.MODEL,
        'predictor_blob': v1.BLOB,
        'temperature': v1.TEMP,
        'selection_rule': str(SELECTION_RULE),
        'parent_regime_preregistration': 'v3/historical_all_market/research_candidates/KEIRIN_REGIME_EXPLANATORY_VALIDATION_PREREGISTRATION_20260913_v1.json',
        'selected_count': len(frozen),
        'result_access_before_lock': False,
        'payout_access': False,
        'odds_used': False,
        'retune': False,
        'post_result_deletion': False,
        'entropy_bins': ['[0,0.70)', '[0.70,0.85)', '[0.85,1.0000001]'],
        'top1_margin_bins': ['[0,0.05)', '[0.05,0.15)', '[0.15,1.0]'],
        'races': frozen,
    }
    (OUT / 'PREDICTION_LOCK.json').write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    scored: list[dict] = []
    result_failures: list[dict] = []
    for r in frozen:
        try:
            winner = v1.parse_winner(v1.fetch(v1.result_url(r['race_id'], r['source_url'])))
            rank = next(i + 1 for i, q in enumerate(r['ranking']) if q['car_no'] == winner)
            pw = next(float(q['p_win']) for q in r['ranking'] if q['car_no'] == winner)
            scored.append({
                'race_id': r['race_id'],
                'meeting_id': r['meeting_id'],
                'meeting_day_index': r['meeting_day_index'],
                'race_no': r['race_no'],
                'venue': r['venue'],
                'circumference_m': r['circumference_m'],
                'winner_car': winner,
                'winner_rank': rank,
                'winner_probability': pw,
                'top1_hit': rank == 1,
                'top3_hit': rank <= 3,
                'log_loss': -math.log(max(pw, 1e-15)),
                'regime': r['regime'],
            })
        except Exception as e:
            result_failures.append({'race_id': r['race_id'], 'reason': str(e)})

    by_entropy = grouped(scored, lambda x: x['regime']['model_normalized_entropy_bin'])
    by_day = grouped(scored, lambda x: x['meeting_day_index'])
    by_margin = grouped(scored, lambda x: x['regime']['model_top1_margin_bin'])

    report = {
        'record': 'KEIRIN_REGIME_SIGNAL_CONFIRMATION_FIXED_MEETINGS_B1A_SCORE_v1',
        'status': 'COMPLETE' if len(scored) == len(frozen) else 'PARTIAL_RESULT_FETCH_FAIL_CLOSED',
        'evidence_class': 'RETROSPECTIVE_KR015_REGIME_SIGNAL_CONFIRMATION',
        'integrity': 'All selected PRE inputs, frozen-B1a probabilities/rankings and unchanged preregistered regime bins were written to PREDICTION_LOCK before dedicated result-page scoring. Historical source pages may themselves be outcome-bearing, so no prospective upgrade is claimed.',
        'model': v1.MODEL,
        'predictor_blob': v1.BLOB,
        'selected_count': len(frozen),
        'scored_count': len(scored),
        'result_fetch_failures': result_failures,
        'odds_used': False,
        'payout_used': False,
        'retune': False,
        'post_result_deletion': False,
        'overall': metric(scored),
        'by_field_size': grouped(scored, lambda x: x['regime']['field_size']),
        'by_meeting_day_index': by_day,
        'by_class_coarse': grouped(scored, lambda x: x['regime']['class_coarse']),
        'by_style_signature': grouped(scored, lambda x: x['regime']['style_signature']),
        'by_model_normalized_entropy_bin': by_entropy,
        'by_model_top1_margin_bin': by_margin,
        'by_exact_circumference': grouped(scored, lambda x: x['circumference_m']),
        'by_venue': grouped(scored, lambda x: x['venue']),
        'by_meeting': grouped(scored, lambda x: x['meeting_id']),
        'confirmation_decisions': confirmation_decisions(by_entropy, by_day),
        'race_scores': scored,
    }
    (OUT / 'SCORE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('REGIME_SIGNAL_CONFIRMATION_SUMMARY=' + json.dumps({
        'status': report['status'],
        'selected_count': report['selected_count'],
        'scored_count': report['scored_count'],
        'overall': report['overall'],
        'by_model_normalized_entropy_bin': report['by_model_normalized_entropy_bin'],
        'by_meeting_day_index': report['by_meeting_day_index'],
        'by_model_top1_margin_bin': report['by_model_top1_margin_bin'],
        'by_exact_circumference': report['by_exact_circumference'],
        'by_venue': report['by_venue'],
        'by_meeting': report['by_meeting'],
        'confirmation_decisions': report['confirmation_decisions'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
