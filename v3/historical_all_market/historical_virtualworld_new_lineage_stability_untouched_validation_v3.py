from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

import historical_virtualworld_100_b1a_v1 as b1a
import historical_virtualworld_100_b1a_v2 as b1a_v2  # noqa: F401; installs hardened result parser

ROOT = Path('v3/historical_all_market/research_candidates')
SEED = Path('.github/workflows/races.csv')
B3 = ROOT / 'KEIRIN_INDEPENDENT_MEETING_REPLICATION_100_B1A_COMPLETE_AUDIT_20260913_v1.json'
B4 = ROOT / 'KEIRIN_COVERAGE_BALANCED_INDEPENDENT_MEETING_100_B1A_COMPLETE_AUDIT_20260913_v2.json'
B5 = ROOT / 'KEIRIN_REGIME_VALIDATION_FIXED_MEETINGS_B1A_COMPLETE_AUDIT_20260913_v1.json'
B6 = ROOT / 'KEIRIN_REGIME_SIGNAL_CONFIRMATION_FIXED_MEETINGS_B1A_COMPLETE_AUDIT_20260913_v1.json'
NL1_FREEZE = ROOT / 'KEIRIN_NEW_LINEAGE_MODEL_FREEZE_20260913_v1.json'
NL1_VALIDATION_AUDIT = ROOT / 'KEIRIN_NEW_LINEAGE_UNTOUCHED_VALIDATION_COMPLETE_AUDIT_20260913_v1.json'
NL2_FREEZE = ROOT / 'KEIRIN_NEW_LINEAGE_STABILITY_MODEL_FREEZE_20260913_v2.json'
RULE = ROOT / 'KEIRIN_NEW_LINEAGE_STABILITY_UNTOUCHED_VALIDATION_SELECTION_RULE_20260913_v3.json'
OUT = ROOT / 'new_lineage_stability_untouched_validation_v3'
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_NL1_CORE_SHA = '53608ed299e5148f215f1a199d897ac1d8320e04707ccb7453c67ced04080671'
EXPECTED_NL2_CORE_SHA = 'e8d969a43c0adddcdf09374d1686a763dbce6d07745576da031849e22c8fb9d0'
EXPLICIT_SMALL = {
    '2220260809', '2220260815', '2220260912',
    '2520260427', '2520260522', '2520260701',
    '2420260521', '7420260629',
}
RETIRED_V2_TARGETS = {'1220260807', '2320260811', '2820260825', '6120260826', '8720260828'}


def load_json(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f'required_canonical_artifact_missing_{path}')
    return json.loads(path.read_text(encoding='utf-8'))


def meeting_from_url(url: str) -> str:
    parts = urlparse(url).path.strip('/').split('/')
    return parts[-4]


def prior_meetings() -> tuple[set[str], dict[str, list[str]]]:
    required = [SEED, B3, B4, B5, B6, NL1_FREEZE, NL1_VALIDATION_AUDIT, NL2_FREEZE, RULE]
    missing = [str(x) for x in required if not x.exists()]
    if missing:
        raise RuntimeError('required_collision_artifact_missing_fail_closed_' + '|'.join(missing))

    sources: dict[str, list[str]] = {}
    seed_meetings = sorted({meeting_from_url(x['url']) for x in csv.DictReader(SEED.read_text(encoding='utf-8').splitlines())})
    sources['seed_and_temporal_meetings'] = seed_meetings

    b3 = load_json(B3)
    sources['batch3_meetings'] = sorted({str(x['meeting_id']) for x in b3['selection']['selected_meetings']})

    b4 = load_json(B4)
    b4_meetings: set[str] = set()
    for meetings in b4['selection']['selected_unique_meetings_by_venue'].values():
        b4_meetings.update(str(x) for x in meetings)
    sources['batch4_meetings'] = sorted(b4_meetings)

    b5 = load_json(B5)
    sources['batch5_meetings'] = sorted(str(x) for x in b5['key_preregistered_slices']['meeting'].keys())

    b6 = load_json(B6)
    sources['batch6_meetings'] = sorted(str(x) for x in b6['descriptive_slices']['meeting'].keys())

    nl1 = load_json(NL1_FREEZE)
    if nl1.get('model_core_sha256') != EXPECTED_NL1_CORE_SHA:
        raise RuntimeError('nl1_model_core_sha_mismatch_fail_closed')
    sources['nl1_development_meetings'] = sorted(str(x) for x in nl1['fit_on_meetings'])

    nl1_val = load_json(NL1_VALIDATION_AUDIT)
    sources['nl1_failed_validation_meetings'] = sorted(str(x['meeting_id']) for x in nl1_val['selection_integrity']['fixed_meetings'])

    nl2 = load_json(NL2_FREEZE)
    if nl2.get('model_core_sha256') != EXPECTED_NL2_CORE_SHA:
        raise RuntimeError('nl2_model_core_sha_mismatch_fail_closed')
    sources['nl2_development_meetings'] = sorted(str(x) for x in nl2['fit_on_meetings'])
    sources['explicit_smaller_exposed_meetings'] = sorted(EXPLICIT_SMALL)
    sources['retired_v2_target_meetings'] = sorted(RETIRED_V2_TARGETS)

    prior: set[str] = set()
    for values in sources.values():
        prior.update(values)
    return prior, sources


def race_url(meeting: str, day_index: int, race_no: int) -> str:
    day = f'{meeting}{day_index:02d}00'
    return f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{race_no:02d}/3rentan/'


def zvals(values: list[float]) -> np.ndarray:
    a = np.array(values, dtype=float)
    sd = float(a.std())
    return (a - float(a.mean())) / (sd if sd else 1.0)


def load_models() -> tuple[dict, dict]:
    nl1 = load_json(NL1_FREEZE)
    if nl1.get('status') != 'FROZEN_AFTER_DEVELOPMENT_SELECTION_BEFORE_UNTOUCHED_VALIDATION':
        raise RuntimeError('nl1_freeze_status_invalid')
    if nl1.get('model_name') != 'NL1_NUMERIC_CLASS_STYLE_L2_V1':
        raise RuntimeError('nl1_model_name_mismatch')
    if nl1.get('model_core_sha256') != EXPECTED_NL1_CORE_SHA:
        raise RuntimeError('nl1_model_core_sha_mismatch')
    if nl1.get('validation_outcomes_accessed_for_this_model') is not False:
        raise RuntimeError('nl1_pre_freeze_validation_outcome_state_invalid')

    nl2 = load_json(NL2_FREEZE)
    if nl2.get('status') != 'FROZEN_AFTER_DEVELOPMENT_SELECTION_BEFORE_FRESH_UNTOUCHED_VALIDATION':
        raise RuntimeError('nl2_freeze_status_invalid')
    if nl2.get('model_name') != 'NL2_GEOBLEND_NUMERIC_L2_3_V1':
        raise RuntimeError('nl2_model_name_mismatch')
    if nl2.get('model_core_sha256') != EXPECTED_NL2_CORE_SHA:
        raise RuntimeError('nl2_model_core_sha_mismatch')
    if nl2.get('fresh_validation_outcomes_accessed_for_this_model') is not False:
        raise RuntimeError('nl2_fresh_validation_outcome_state_not_clean')
    if nl2.get('dev2000_used') is not False or nl2.get('econ_holdout1000_used') is not False:
        raise RuntimeError('nl2_protected_evidence_firewall_invalid')
    if nl2.get('source_model_nl1_core_sha256') != EXPECTED_NL1_CORE_SHA:
        raise RuntimeError('nl2_source_nl1_sha_mismatch')
    return nl1, nl2


def predict_nl1(rows: list[dict], freeze: dict) -> list[dict]:
    numeric = list(freeze['numeric_features'])
    class_levels = list(freeze['class_levels'])
    style_levels = list(freeze['style_levels'])
    w = np.array(freeze['coefficients'], dtype=float)
    cols = [zvals([float(r[name]) for r in rows]) for name in numeric]
    X = np.column_stack(cols)
    X = np.column_stack([
        X,
        np.array([[1.0 if str(r['class']) == level else 0.0 for level in class_levels] for r in rows], dtype=float),
        np.array([[1.0 if str(r['style']) == level else 0.0 for level in style_levels] for r in rows], dtype=float),
    ])
    if X.shape[1] != len(w):
        raise RuntimeError(f'nl1_feature_count_mismatch_{X.shape[1]}_{len(w)}')
    scores = X @ w
    probs = np.exp(scores - float(scores.max()))
    probs = probs / float(probs.sum())
    out = [{'car_no': int(r['car_no']), 'p_win': float(p)} for r, p in zip(rows, probs)]
    return sorted(out, key=lambda x: (-x['p_win'], x['car_no']))


def predict_nl2(rows: list[dict], b1a_ranking: list[dict], nl1_ranking: list[dict], freeze: dict) -> list[dict]:
    expected_features = ['nl1_minus_b1a_logprob', 'score', 'win_rate', 'top2_rate', 'top3_rate', 'B', 'S']
    if list(freeze['features']) != expected_features:
        raise RuntimeError('nl2_feature_order_mismatch')
    w = np.array(freeze['coefficients'], dtype=float)
    if len(w) != len(expected_features):
        raise RuntimeError('nl2_coefficient_count_mismatch')

    pb = {int(x['car_no']): float(x['p_win']) for x in b1a_ranking}
    pn = {int(x['car_no']): float(x['p_win']) for x in nl1_ranking}
    blend = np.array([
        math.log(max(pn[int(r['car_no'])], 1e-300)) - math.log(max(pb[int(r['car_no'])], 1e-300))
        for r in rows
    ], dtype=float)
    numeric_names = ['score', 'win_rate', 'top2_rate', 'top3_rate', 'B', 'S']
    numeric_cols = [zvals([float(r[name]) for r in rows]) for name in numeric_names]
    X = np.column_stack([blend, *numeric_cols])
    correction = X @ w
    anchored = np.array([math.log(max(pb[int(r['car_no'])], 1e-300)) for r in rows], dtype=float) + correction
    probs = np.exp(anchored - float(anchored.max()))
    probs = probs / float(probs.sum())
    out = [{'car_no': int(r['car_no']), 'p_win': float(p)} for r, p in zip(rows, probs)]
    return sorted(out, key=lambda x: (-x['p_win'], x['car_no']))


def freeze_race(target: dict, day_index: int, race_no: int, nl1: dict, nl2: dict) -> dict:
    meeting = str(target['meeting_id'])
    venue = str(target['venue'])
    rid = f'NL2VAL3_{meeting}_{venue}_{day_index:02d}_{race_no:02d}R'
    url = race_url(meeting, day_index, race_no)
    payload = b1a.fetch(url)
    rows, parsed_venue, circ = b1a.parse_pre(rid, url, payload)
    if parsed_venue != venue:
        raise RuntimeError(f'venue_mismatch_{parsed_venue}_{venue}')
    expected_circ = float(target['circumference_m'])
    if abs(float(circ) - expected_circ) > 1e-9:
        raise RuntimeError(f'circumference_mismatch_{circ}_{expected_circ}')
    b1a_ranking = b1a.predict(rows)
    nl1_ranking = predict_nl1(rows, nl1)
    nl2_ranking = predict_nl2(rows, b1a_ranking, nl1_ranking, nl2)
    return {
        'race_id': rid,
        'source_url': url,
        'meeting_id': meeting,
        'meeting_day_index': day_index,
        'race_no': race_no,
        'venue': venue,
        'circumference_m': float(circ),
        'inputs': rows,
        'nl2_ranking': nl2_ranking,
        'b1a_ranking': b1a_ranking,
    }


def score_model(ranking: list[dict], winner: int) -> dict:
    rank = next(i + 1 for i, q in enumerate(ranking) if int(q['car_no']) == winner)
    p = next(float(q['p_win']) for q in ranking if int(q['car_no']) == winner)
    return {
        'winner_rank': rank,
        'winner_probability': p,
        'top1_hit': rank == 1,
        'top3_hit': rank <= 3,
        'log_loss': -math.log(max(p, 1e-300)),
    }


def metric(rows: list[dict], key: str) -> dict:
    n = len(rows)
    if not n:
        return {'n': 0, 'top1_hits': 0, 'top1_accuracy': None, 'winner_top3': 0, 'top3_rate': None, 'mean_log_loss': None}
    vals = [r[key] for r in rows]
    return {
        'n': n,
        'top1_hits': sum(bool(x['top1_hit']) for x in vals),
        'top1_accuracy': sum(bool(x['top1_hit']) for x in vals) / n,
        'winner_top3': sum(bool(x['top3_hit']) for x in vals),
        'top3_rate': sum(bool(x['top3_hit']) for x in vals) / n,
        'mean_log_loss': sum(float(x['log_loss']) for x in vals) / n,
    }


def grouped(rows: list[dict], group_key: str, model_key: str) -> dict:
    groups = sorted({str(r[group_key]) for r in rows})
    return {g: metric([r for r in rows if str(r[group_key]) == g], model_key) for g in groups}


def decision(scored: list[dict], by_meeting_nl2: dict, by_meeting_b1a: dict) -> dict:
    nl2m = metric(scored, 'nl2')
    base = metric(scored, 'b1a')
    meeting_counts = Counter(str(r['meeting_id']) for r in scored)
    coverage_ok = len(scored) >= 110 and len(meeting_counts) == 5 and all(n >= 15 for n in meeting_counts.values())
    if not coverage_ok:
        return {
            'status': 'INCONCLUSIVE_RESULT_COVERAGE',
            'interpretability_gate_pass': False,
            'scored_count': len(scored),
            'scored_by_meeting': dict(sorted(meeting_counts.items())),
        }

    meetings_improved = [m for m in sorted(by_meeting_nl2) if by_meeting_nl2[m]['mean_log_loss'] < by_meeting_b1a[m]['mean_log_loss']]
    c1_delta = base['mean_log_loss'] - nl2m['mean_log_loss']
    c1 = c1_delta >= 0.02
    c2 = len(meetings_improved) >= 3
    c3_delta = nl2m['top3_rate'] - base['top3_rate']
    c3 = c3_delta >= -0.02
    c4_delta = nl2m['top1_accuracy'] - base['top1_accuracy']
    c4 = c4_delta >= -0.02
    status = 'PASS_UNTOUCHED_VALIDATION' if all([c1, c2, c3, c4]) else 'FAIL_UNTOUCHED_VALIDATION'
    return {
        'status': status,
        'interpretability_gate_pass': True,
        'criteria': {
            'C1_POOLED_LOG_LOSS': {'pass': c1, 'b1a_minus_nl2_log_loss': c1_delta, 'required_minimum': 0.02},
            'C2_MEETING_STABILITY': {'pass': c2, 'meetings_nl2_lower_log_loss': meetings_improved, 'count': len(meetings_improved), 'required_minimum': 3},
            'C3_TOP3_NONINFERIORITY': {'pass': c3, 'nl2_minus_b1a_top3_rate': c3_delta, 'minimum_allowed': -0.02},
            'C4_TOP1_NONINFERIORITY': {'pass': c4, 'nl2_minus_b1a_top1_accuracy': c4_delta, 'minimum_allowed': -0.02},
        },
    }


def main() -> None:
    rule = load_json(RULE)
    if rule.get('status') != 'PREREGISTERED_BEFORE_TARGET_PRE_FREEZE_AND_DEDICATED_RESULT_SCORING':
        raise RuntimeError('validation_rule_status_invalid')
    if rule.get('model_core_sha256') != EXPECTED_NL2_CORE_SHA:
        raise RuntimeError('validation_rule_model_sha_mismatch')
    fixed = list(rule['fixed_meetings'])
    if len(fixed) != 5 or len({str(x['meeting_id']) for x in fixed}) != 5:
        raise RuntimeError('validation_fixed_meeting_count_or_uniqueness_invalid')

    for target in fixed:
        b1a.CIRC[str(target['venue'])] = float(target['circumference_m'])

    prior, collision_sources = prior_meetings()
    fixed_ids = {str(x['meeting_id']) for x in fixed}
    overlap = sorted(fixed_ids & prior)
    if overlap:
        raise RuntimeError('fixed_validation_prior_meeting_overlap_' + '_'.join(overlap))

    nl1, nl2 = load_models()
    frozen: list[dict] = []
    rejected: list[dict] = []
    for target in fixed:
        for day_index in rule['selection']['enumerate_days']:
            for race_no in rule['selection']['enumerate_races']:
                try:
                    frozen.append(freeze_race(target, int(day_index), int(race_no), nl1, nl2))
                except Exception as e:
                    rejected.append({
                        'meeting_id': str(target['meeting_id']),
                        'venue': str(target['venue']),
                        'day_index': int(day_index),
                        'race_no': int(race_no),
                        'reason': str(e),
                    })

    selected_by_meeting = dict(sorted(Counter(r['meeting_id'] for r in frozen).items()))
    selection_audit = {
        'record': 'KEIRIN_NEW_LINEAGE_STABILITY_UNTOUCHED_VALIDATION_SELECTION_EXECUTION_v3',
        'evidence_class': 'RETROSPECTIVE_KR015_UNTOUCHED_NL2_VALIDATION',
        'rule': str(RULE),
        'fixed_meetings': fixed,
        'prior_collision_sources': collision_sources,
        'prior_meeting_count': len(prior),
        'prior_meeting_overlap_count': 0,
        'candidate_count': len(fixed) * len(rule['selection']['enumerate_days']) * len(rule['selection']['enumerate_races']),
        'selected_count': len(frozen),
        'selected_unique_meeting_count': len(selected_by_meeting),
        'selected_by_meeting': selected_by_meeting,
        'selected_by_venue': dict(sorted(Counter(r['venue'] for r in frozen).items())),
        'selected_by_exact_circumference': dict(sorted(Counter(str(r['circumference_m']) for r in frozen).items())),
        'selected_by_field_size': dict(sorted(Counter(str(len(r['inputs'])) for r in frozen).items())),
        'dedicated_result_access_during_selection': False,
        'payout_access_during_selection': False,
        'odds_used_as_predictor': False,
        'pre_only_rejections_retained': rejected,
    }
    (OUT / 'SELECTION_AUDIT.json').write_text(json.dumps(selection_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    minimum_frozen = int(rule['selection']['minimum_frozen_races'])
    if len(frozen) < minimum_frozen:
        raise RuntimeError(f'validation_selected_{len(frozen)}_below_preregistered_minimum_{minimum_frozen}')
    if len(selected_by_meeting) != 5:
        raise RuntimeError(f'validation_selected_meetings_{len(selected_by_meeting)}_expected_5')

    prediction_lock = {
        'record': 'KEIRIN_NEW_LINEAGE_STABILITY_UNTOUCHED_VALIDATION_PREDICTION_LOCK_v3',
        'evidence_class': 'RETROSPECTIVE_KR015_UNTOUCHED_NL2_VALIDATION',
        'selection_rule': str(RULE),
        'new_lineage_model': {
            'name': nl2['model_name'],
            'model_core_sha256': nl2['model_core_sha256'],
            'freeze': str(NL2_FREEZE),
        },
        'source_nl1_model': {
            'name': nl1['model_name'],
            'model_core_sha256': nl1['model_core_sha256'],
            'freeze': str(NL1_FREEZE),
        },
        'baseline_model': {
            'name': b1a.MODEL,
            'predictor_blob': b1a.BLOB,
            'temperature': b1a.TEMP,
        },
        'selected_count': len(frozen),
        'dedicated_result_access_before_lock': False,
        'historical_source_page_warning': 'Kdreams historical PRE-source pages may themselves be outcome-bearing; KR-015 retrospective classification is retained. No dedicated result URL is fetched until after this lock is written.',
        'payout_access': False,
        'odds_used_as_predictor': False,
        'nl2_retune': False,
        'b1a_retune': False,
        'post_result_deletion': False,
        'races': frozen,
    }
    (OUT / 'PREDICTION_LOCK.json').write_text(json.dumps(prediction_lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    scored: list[dict] = []
    result_failures: list[dict] = []
    for r in frozen:
        try:
            winner = b1a.parse_winner(b1a.fetch(b1a.result_url(r['race_id'], r['source_url'])))
            scored.append({
                'race_id': r['race_id'],
                'meeting_id': r['meeting_id'],
                'meeting_day_index': r['meeting_day_index'],
                'race_no': r['race_no'],
                'venue': r['venue'],
                'circumference_m': r['circumference_m'],
                'winner_car': winner,
                'nl2': score_model(r['nl2_ranking'], winner),
                'b1a': score_model(r['b1a_ranking'], winner),
            })
        except Exception as e:
            result_failures.append({'race_id': r['race_id'], 'meeting_id': r['meeting_id'], 'reason': str(e)})

    by_meeting_nl2 = grouped(scored, 'meeting_id', 'nl2')
    by_meeting_b1a = grouped(scored, 'meeting_id', 'b1a')
    report = {
        'record': 'KEIRIN_NEW_LINEAGE_STABILITY_UNTOUCHED_VALIDATION_SCORE_v3',
        'status': 'SCORED_WITH_PREREGISTERED_DECISION',
        'evidence_class': 'RETROSPECTIVE_KR015_UNTOUCHED_NL2_VALIDATION',
        'integrity': 'All mandatory PRE inputs plus frozen NL2 and B1a probabilities/rankings were written to PREDICTION_LOCK before dedicated result scoring. Historical source pages may themselves expose outcomes, so this remains KR-015 retrospective evidence. No target result is used for model fitting, target replacement, or retuning.',
        'selected_count': len(frozen),
        'scored_count': len(scored),
        'result_fetch_failures': result_failures,
        'odds_used_as_predictor': False,
        'payout_used': False,
        'nl2_retune': False,
        'b1a_retune': False,
        'post_result_deletion': False,
        'nl2_overall': metric(scored, 'nl2'),
        'b1a_overall': metric(scored, 'b1a'),
        'nl2_by_meeting': by_meeting_nl2,
        'b1a_by_meeting': by_meeting_b1a,
        'nl2_by_exact_circumference': grouped(scored, 'circumference_m', 'nl2'),
        'b1a_by_exact_circumference': grouped(scored, 'circumference_m', 'b1a'),
        'nl2_by_venue': grouped(scored, 'venue', 'nl2'),
        'b1a_by_venue': grouped(scored, 'venue', 'b1a'),
        'decision': decision(scored, by_meeting_nl2, by_meeting_b1a),
        'race_scores': scored,
    }
    (OUT / 'SCORE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('NL2_UNTOUCHED_VALIDATION_V3_SUMMARY=' + json.dumps({
        'selected_count': report['selected_count'],
        'scored_count': report['scored_count'],
        'result_failure_count': len(result_failures),
        'nl2_overall': report['nl2_overall'],
        'b1a_overall': report['b1a_overall'],
        'nl2_by_meeting': report['nl2_by_meeting'],
        'b1a_by_meeting': report['b1a_by_meeting'],
        'decision': report['decision'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
