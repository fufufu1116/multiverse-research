from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

OUT = Path('v3/historical_all_market/research_candidates/new_lineage_architecture_development_v1')
OUT.mkdir(parents=True, exist_ok=True)

PREREG = 'v3/historical_all_market/research_candidates/KEIRIN_NEW_LINEAGE_ARCHITECTURE_DEVELOPMENT_PREREGISTRATION_20260913_v1.json'
EXPECTED_ZIP_SHA = {
    'batch5': '882657a256f843876879f667b13342c9e5151c9afa84896e17addac9cfe1b925',
    'batch6': 'fd0f320775efab8079d3fd076531fd7dc8ef2cae93ae207c3a125ca06222a91b',
}
EXPECTED_COUNTS = {'selected': 321, 'labelled': 320, 'meetings': 11}
NUM_ALL = ['score', 'win_rate', 'top2_rate', 'top3_rate', 'B', 'S']
CLASS_LEVELS = ['A1', 'A2', 'A3', 'L1', 'S1', 'S2', 'SS']
STYLE_LEVELS = ['逃', '追', '両']
CANDIDATES = {
    'NL1_REDUCED_L2_V1': {'numeric': ['score', 'win_rate', 'top3_rate'], 'categorical': [], 'l2_lambda': 1.0},
    'NL1_NUMERIC_L2_V1': {'numeric': NUM_ALL, 'categorical': [], 'l2_lambda': 1.0},
    'NL1_NUMERIC_CLASS_STYLE_L2_V1': {'numeric': NUM_ALL, 'categorical': ['class', 'style'], 'l2_lambda': 1.0},
    'NL1_SCORE_ONLY_L2_V1': {'numeric': ['score'], 'categorical': [], 'l2_lambda': 1.0},
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj) -> str:
    b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()


def load_artifact(path: Path, batch: str) -> tuple[dict, dict, dict]:
    got = sha256_file(path)
    expected = EXPECTED_ZIP_SHA[batch]
    if got != expected:
        raise RuntimeError(f'{batch}_artifact_sha_mismatch_{got}_{expected}')
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        required = {'PREDICTION_LOCK.json', 'SCORE.json', 'SELECTION_AUDIT.json'}
        if not required <= names:
            raise RuntimeError(f'{batch}_artifact_required_files_missing_{sorted(required - names)}')
        return tuple(json.loads(z.read(n)) for n in ('PREDICTION_LOCK.json', 'SCORE.json', 'SELECTION_AUDIT.json'))


def build_dataset(batch5_zip: Path, batch6_zip: Path) -> tuple[list[dict], dict]:
    races: list[dict] = []
    source_audit = {}
    for batch, path in [('batch5', batch5_zip), ('batch6', batch6_zip)]:
        lock, score, sel = load_artifact(path, batch)
        winners = {x['race_id']: int(x['winner_car']) for x in score['race_scores']}
        for r in lock['races']:
            races.append({
                'source_batch': batch,
                'race_id': str(r['race_id']),
                'meeting_id': str(r['meeting_id']),
                'venue': str(r['venue']),
                'circumference_m': float(r['circumference_m']),
                'inputs': r['inputs'],
                'b1a_ranking': r['ranking'],
                'winner_car': winners.get(r['race_id']),
            })
        source_audit[batch] = {
            'zip_sha256': EXPECTED_ZIP_SHA[batch],
            'selected_count': int(lock['selected_count']),
            'scored_count': int(score['scored_count']),
            'result_failure_count': len(score.get('result_fetch_failures', [])),
            'selection_prior_meeting_overlap_count': int(sel.get('prior_meeting_overlap_count', 0)),
        }

    ids = [r['race_id'] for r in races]
    duplicates = sorted(k for k, v in Counter(ids).items() if v > 1)
    if duplicates:
        raise RuntimeError('duplicate_race_ids_' + '_'.join(duplicates[:20]))

    labelled = [r for r in races if r['winner_car'] is not None]
    meetings = sorted({r['meeting_id'] for r in labelled})
    if len(races) != EXPECTED_COUNTS['selected']:
        raise RuntimeError(f'selected_count_{len(races)}_expected_{EXPECTED_COUNTS["selected"]}')
    if len(labelled) != EXPECTED_COUNTS['labelled']:
        raise RuntimeError(f'labelled_count_{len(labelled)}_expected_{EXPECTED_COUNTS["labelled"]}')
    if len(meetings) != EXPECTED_COUNTS['meetings']:
        raise RuntimeError(f'meeting_count_{len(meetings)}_expected_{EXPECTED_COUNTS["meetings"]}')

    missing_labels = [r['race_id'] for r in races if r['winner_car'] is None]
    compact_fingerprint_payload = []
    for r in sorted(races, key=lambda x: x['race_id']):
        compact_fingerprint_payload.append({
            'race_id': r['race_id'],
            'meeting_id': r['meeting_id'],
            'winner_car': r['winner_car'],
            'inputs': [
                [int(x['car_no']), str(x['class']), str(x['style']), float(x['score']), float(x['S']), float(x['B']), float(x['win_rate']), float(x['top2_rate']), float(x['top3_rate'])]
                for x in r['inputs']
            ],
        })

    dataset_audit = {
        'record': 'KEIRIN_NEW_LINEAGE_DEVELOPMENT_DATASET_AUDIT_v1',
        'evidence_class': 'DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION',
        'preregistration': PREREG,
        'sources': source_audit,
        'selected_count': len(races),
        'labelled_count': len(labelled),
        'unlabelled_retained_count': len(missing_labels),
        'unlabelled_retained_race_ids': missing_labels,
        'unique_race_ids': len(set(ids)),
        'unique_meetings': len(meetings),
        'meeting_ids': meetings,
        'labelled_by_meeting': dict(sorted(Counter(r['meeting_id'] for r in labelled).items())),
        'duplicate_race_ids': duplicates,
        'development_dataset_sha256': canonical_sha(compact_fingerprint_payload),
        'protected_evidence_used': false if False else False,
        'dev2000_used': False,
        'econ_holdout1000_used': False,
    }
    return labelled, dataset_audit


def zvals(vals: list[float]) -> np.ndarray:
    a = np.array(vals, dtype=float)
    sd = float(a.std())
    return (a - float(a.mean())) / (sd if sd else 1.0)


def design(race: dict, numeric: list[str], categorical: list[str]) -> tuple[np.ndarray, int, np.ndarray]:
    rows = race['inputs']
    cols = [zvals([float(x[name]) for x in rows]) for name in numeric]
    X = np.column_stack(cols) if cols else np.zeros((len(rows), 0), dtype=float)
    if 'class' in categorical:
        X = np.column_stack([X, np.array([[1.0 if str(x['class']) == level else 0.0 for level in CLASS_LEVELS] for x in rows])])
    if 'style' in categorical:
        X = np.column_stack([X, np.array([[1.0 if str(x['style']) == level else 0.0 for level in STYLE_LEVELS] for x in rows])])
    cars = np.array([int(x['car_no']) for x in rows], dtype=int)
    winner = int(race['winner_car'])
    matches = np.where(cars == winner)[0]
    if len(matches) != 1:
        raise RuntimeError(f'winner_car_not_unique_{race["race_id"]}_{winner}')
    return X, int(matches[0]), cars


def fit_model(train: list[dict], spec: dict) -> tuple[np.ndarray, dict]:
    prepared = [design(r, spec['numeric'], spec['categorical']) for r in train]
    d = prepared[0][0].shape[1]
    lam = float(spec['l2_lambda'])

    def objective(w: np.ndarray):
        loss = 0.0
        grad = np.zeros(d, dtype=float)
        for X, y, _ in prepared:
            s = X @ w
            s = s - float(np.max(s))
            p = np.exp(s)
            p = p / float(np.sum(p))
            loss += -math.log(max(float(p[y]), 1e-300))
            grad += X.T @ p - X[y]
        n = len(prepared)
        loss /= n
        grad /= n
        if d:
            loss += 0.5 * lam * float(np.mean(w * w))
            grad += lam * w / d
        return loss, grad

    result = minimize(
        fun=lambda w: objective(w),
        x0=np.zeros(d, dtype=float),
        jac=True,
        method='L-BFGS-B',
        options={'maxiter': 2000, 'ftol': 1e-12},
    )
    if not result.success:
        raise RuntimeError(f'optimizer_failed_{result.message}')
    return np.array(result.x, dtype=float), {
        'success': bool(result.success),
        'iterations': int(result.nit),
        'objective': float(result.fun),
        'coefficient_count': d,
    }


def score_linear(test: list[dict], w: np.ndarray, spec: dict) -> list[dict]:
    out = []
    for r in test:
        X, y, cars = design(r, spec['numeric'], spec['categorical'])
        s = X @ w
        p = np.exp(s - float(np.max(s)))
        p = p / float(np.sum(p))
        order = np.lexsort((cars, -p))
        ranked_cars = cars[order]
        winner = int(r['winner_car'])
        rank = int(np.where(ranked_cars == winner)[0][0] + 1)
        pw = float(p[y])
        out.append({
            'race_id': r['race_id'],
            'meeting_id': r['meeting_id'],
            'winner_car': winner,
            'winner_rank': rank,
            'winner_probability': pw,
            'top1_hit': rank == 1,
            'top3_hit': rank <= 3,
            'log_loss': -math.log(max(pw, 1e-300)),
        })
    return out


def score_b1a(test: list[dict]) -> list[dict]:
    out = []
    for r in test:
        ranking = sorted(r['b1a_ranking'], key=lambda q: (-float(q['p_win']), int(q['car_no'])))
        winner = int(r['winner_car'])
        rank = next(i + 1 for i, q in enumerate(ranking) if int(q['car_no']) == winner)
        pw = next(float(q['p_win']) for q in ranking if int(q['car_no']) == winner)
        out.append({
            'race_id': r['race_id'],
            'meeting_id': r['meeting_id'],
            'winner_car': winner,
            'winner_rank': rank,
            'winner_probability': pw,
            'top1_hit': rank == 1,
            'top3_hit': rank <= 3,
            'log_loss': -math.log(max(pw, 1e-300)),
        })
    return out


def metric(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        'n': n,
        'top1_hits': sum(bool(x['top1_hit']) for x in rows),
        'top1_accuracy': sum(bool(x['top1_hit']) for x in rows) / n,
        'winner_top3': sum(bool(x['top3_hit']) for x in rows),
        'top3_rate': sum(bool(x['top3_hit']) for x in rows) / n,
        'mean_log_loss': sum(float(x['log_loss']) for x in rows) / n,
    }


def meeting_metrics(rows: list[dict]) -> dict:
    meetings = sorted({x['meeting_id'] for x in rows})
    return {m: metric([x for x in rows if x['meeting_id'] == m]) for m in meetings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch5-zip', required=True)
    parser.add_argument('--batch6-zip', required=True)
    args = parser.parse_args()

    labelled, dataset_audit = build_dataset(Path(args.batch5_zip), Path(args.batch6_zip))
    meetings = sorted({r['meeting_id'] for r in labelled})

    baseline_rows = score_b1a(labelled)
    baseline_overall = metric(baseline_rows)
    baseline_by_meeting = meeting_metrics(baseline_rows)

    candidates_report = {}
    eligible = []
    for candidate_id, spec in CANDIDATES.items():
        heldout_rows = []
        folds = []
        for heldout_meeting in meetings:
            train = [r for r in labelled if r['meeting_id'] != heldout_meeting]
            test = [r for r in labelled if r['meeting_id'] == heldout_meeting]
            w, fit_info = fit_model(train, spec)
            scored = score_linear(test, w, spec)
            heldout_rows.extend(scored)
            folds.append({
                'heldout_meeting': heldout_meeting,
                'train_races': len(train),
                'test_races': len(test),
                'fit': fit_info,
                'metrics': metric(scored),
            })

        overall = metric(heldout_rows)
        by_meeting = meeting_metrics(heldout_rows)
        improved_meetings = [m for m in meetings if by_meeting[m]['mean_log_loss'] < baseline_by_meeting[m]['mean_log_loss']]
        meeting_lls = [by_meeting[m]['mean_log_loss'] for m in meetings]
        ll_improvement = baseline_overall['mean_log_loss'] - overall['mean_log_loss']
        top3_delta = overall['top3_rate'] - baseline_overall['top3_rate']
        is_eligible = ll_improvement >= 0.015 and len(improved_meetings) >= 6 and top3_delta >= -0.02
        candidates_report[candidate_id] = {
            'spec': spec,
            'overall_heldout': overall,
            'by_meeting_heldout': by_meeting,
            'folds': folds,
            'pooled_log_loss_improvement_vs_b1a': ll_improvement,
            'top3_delta_vs_b1a': top3_delta,
            'meetings_improved_vs_b1a': improved_meetings,
            'meetings_improved_count': len(improved_meetings),
            'median_meeting_log_loss': float(np.median(meeting_lls)),
            'worst_meeting_log_loss': float(max(meeting_lls)),
            'eligible': is_eligible,
        }
        if is_eligible:
            eligible.append(candidate_id)

    if eligible:
        winner = sorted(
            eligible,
            key=lambda cid: (
                candidates_report[cid]['overall_heldout']['mean_log_loss'],
                -candidates_report[cid]['meetings_improved_count'],
                -candidates_report[cid]['overall_heldout']['top1_accuracy'],
                cid,
            ),
        )[0]
        status = 'DEVELOPMENT_SEARCH_PASS_ELIGIBLE_REPLACEMENT_SELECTED'
        spec = CANDIDATES[winner]
        final_w, final_fit = fit_model(labelled, spec)
        feature_names = list(spec['numeric'])
        if 'class' in spec['categorical']:
            feature_names += [f'class={x}' for x in CLASS_LEVELS]
        if 'style' in spec['categorical']:
            feature_names += [f'style={x}' for x in STYLE_LEVELS]
        model_core = {
            'model_name': winner,
            'lineage': 'NEW_LINEAGE_DEVELOPMENT_ONLY_v1',
            'feature_names': feature_names,
            'numeric_features': spec['numeric'],
            'categorical_features': spec['categorical'],
            'class_levels': CLASS_LEVELS if 'class' in spec['categorical'] else [],
            'style_levels': STYLE_LEVELS if 'style' in spec['categorical'] else [],
            'numeric_transform': 'within-race population z-score',
            'probability': 'within-race softmax(linear score)',
            'l2_lambda': spec['l2_lambda'],
            'coefficients': [float(x) for x in final_w],
            'fit_on_labelled_development_races': len(labelled),
            'fit_on_meetings': meetings,
            'development_dataset_sha256': dataset_audit['development_dataset_sha256'],
            'preregistration': PREREG,
        }
        model_hash = canonical_sha(model_core)
        model_freeze = {
            'record': 'KEIRIN_NEW_LINEAGE_MODEL_FREEZE_v1',
            'status': 'FROZEN_AFTER_DEVELOPMENT_SELECTION_BEFORE_UNTOUCHED_VALIDATION',
            **model_core,
            'model_core_sha256': model_hash,
            'final_fit': final_fit,
            'validation_outcomes_accessed_for_this_model': False,
            'runtime': 'OFF',
            'automatic_betting': False,
        }
        (OUT / 'MODEL_FREEZE.json').write_text(json.dumps(model_freeze, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        winner = None
        status = 'DEVELOPMENT_SEARCH_FAIL_NO_ELIGIBLE_REPLACEMENT'
        model_hash = None

    report = {
        'record': 'KEIRIN_NEW_LINEAGE_ARCHITECTURE_DEVELOPMENT_SCORE_v1',
        'status': status,
        'evidence_class': 'DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION',
        'preregistration': PREREG,
        'dataset_audit': dataset_audit,
        'baseline_b1a': {
            'model': 'B1a_RECONSTITUTED_v1',
            'predictor_blob': '62ae4ebc17cda47dca1fffae190fa44caae58ca3',
            'overall': baseline_overall,
            'by_meeting': baseline_by_meeting,
        },
        'candidates': candidates_report,
        'eligible_candidates': eligible,
        'selected_candidate': winner,
        'selected_model_core_sha256': model_hash,
        'selection_rule_applied_exactly': True,
        'fresh_validation_outcomes_used': False,
        'dev2000_used': False,
        'econ_holdout1000_used': False,
        'runtime': 'OFF',
        'automatic_betting': False,
    }
    (OUT / 'DATASET_AUDIT.json').write_text(json.dumps(dataset_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'SCORE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('NEW_LINEAGE_DEVELOPMENT_SUMMARY=' + json.dumps({
        'status': status,
        'dataset': {k: dataset_audit[k] for k in ['selected_count', 'labelled_count', 'unique_meetings', 'development_dataset_sha256']},
        'baseline': baseline_overall,
        'candidates': {cid: {
            'overall': x['overall_heldout'],
            'll_improvement': x['pooled_log_loss_improvement_vs_b1a'],
            'meetings_improved_count': x['meetings_improved_count'],
            'eligible': x['eligible'],
        } for cid, x in candidates_report.items()},
        'selected_candidate': winner,
        'selected_model_core_sha256': model_hash,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
