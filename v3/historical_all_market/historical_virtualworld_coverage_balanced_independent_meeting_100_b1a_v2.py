from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # noqa: F401; installs hardened result parser

v1.CIRC.update({'maebashi': 335.0, 'kawasaki': 400.0})

SEED = Path('.github/workflows/races.csv')
BATCH3_AUDIT = Path('v3/historical_all_market/research_candidates/KEIRIN_INDEPENDENT_MEETING_REPLICATION_100_B1A_COMPLETE_AUDIT_20260913_v1.json')
GEN = Path('.github/workflows/races_coverage_balanced_independent_meeting_100_v2.csv')
OUT = Path('v3/historical_all_market/research_candidates/virtualworld_coverage_balanced_independent_meeting_100_b1a_v2')
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {'code': '12', 'venue': 'aomori', 'circ': 400.0, 'quota': 17, 'meetings': ['1220260824', '1220260903']},
    {'code': '21', 'venue': 'yahiko', 'circ': 400.0, 'quota': 17, 'meetings': ['2120260818', '2120260902']},
    {'code': '22', 'venue': 'maebashi', 'circ': 335.0, 'quota': 17, 'meetings': ['2220260815', '2220260827']},
    {'code': '34', 'venue': 'kawasaki', 'circ': 400.0, 'quota': 17, 'meetings': ['3420260819', '3420260830']},
    {'code': '43', 'venue': 'gifu', 'circ': 400.0, 'quota': 16, 'meetings': ['4320260824', '4320260830']},
    {'code': '46', 'venue': 'toyama', 'circ': 333.3, 'quota': 16, 'meetings': ['4620260820', '4620260903']},
]
MEETING_CAP = 12


def meeting_from_url(url: str) -> str:
    p = urlparse(url).path.strip('/').split('/')
    return p[-4]


def seed_meetings() -> set[str]:
    if not SEED.exists():
        raise RuntimeError('seed_universe_missing_fail_closed')
    return {meeting_from_url(x['url']) for x in csv.DictReader(SEED.read_text(encoding='utf-8').splitlines())}


def batch3_meetings() -> set[str]:
    if not BATCH3_AUDIT.exists():
        raise RuntimeError('batch3_audit_missing_fail_closed')
    audit = json.loads(BATCH3_AUDIT.read_text(encoding='utf-8'))
    return {str(x['meeting_id']) for x in audit.get('selection', {}).get('selected_meetings', [])}


def race_url(meeting: str, di: str, rr: int) -> str:
    day = f'{meeting}{di}00'
    return f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{rr:02d}/3rentan/'


def parse_pre(meeting: str, venue: str, di: str, rr: int):
    rid = f'CBAL2_{meeting}_{venue}_{di}_{rr:02d}R'
    url = race_url(meeting, di, rr)
    payload = v1.fetch(url)
    rows, parsed_venue, circ = v1.parse_pre(rid, url, payload)
    if parsed_venue != venue:
        raise RuntimeError(f'venue_mismatch_{parsed_venue}_{venue}')
    return rid, url, circ, rows


def build_universe():
    prior = seed_meetings() | batch3_meetings()
    fixed = {m for t in TARGETS for m in t['meetings']}
    overlap = sorted(fixed & prior)
    if overlap:
        raise RuntimeError('fixed_prior_meeting_overlap_' + '_'.join(overlap))

    selected: list[dict] = []
    rejected: list[dict] = []
    venue_counts = Counter()
    meeting_counts = Counter()
    venue_meetings: dict[str, set[str]] = defaultdict(set)

    for target in TARGETS:
        venue = target['venue']
        quota = int(target['quota'])
        for meeting in target['meetings']:
            for di in ('01', '02', '03', '04'):
                for rr in range(1, 13):
                    if venue_counts[venue] >= quota or meeting_counts[meeting] >= MEETING_CAP:
                        break
                    try:
                        rid, url, circ, _rows = parse_pre(meeting, venue, di, rr)
                        if abs(float(circ) - float(target['circ'])) > 1e-9:
                            raise RuntimeError(f'circumference_mismatch_{circ}_{target["circ"]}')
                        selected.append({
                            'race_id': rid,
                            'url': url,
                            'meeting_id': meeting,
                            'venue': venue,
                            'exact_circumference_m': circ,
                        })
                        venue_counts[venue] += 1
                        meeting_counts[meeting] += 1
                        venue_meetings[venue].add(meeting)
                    except Exception as e:
                        rejected.append({
                            'meeting_id': meeting,
                            'venue': venue,
                            'day_index': di,
                            'race_no': rr,
                            'reason': str(e),
                        })
                if venue_counts[venue] >= quota or meeting_counts[meeting] >= MEETING_CAP:
                    break

        if venue_counts[venue] != quota:
            raise RuntimeError(f'venue_quota_unfilled_{venue}_{venue_counts[venue]}_expected_{quota}')
        if len(venue_meetings[venue]) != 2:
            raise RuntimeError(f'venue_two_meeting_requirement_failed_{venue}_{len(venue_meetings[venue])}_expected_2')
        if any(meeting_counts[m] == 0 for m in target['meetings']):
            raise RuntimeError(f'fixed_meeting_zero_contribution_{venue}')

    audit = {
        'record': 'KEIRIN_COVERAGE_BALANCED_INDEPENDENT_MEETING_100_V2_SELECTION_EXECUTION',
        'result_access_during_selection': False,
        'payout_access_during_selection': False,
        'odds_used': False,
        'prior_meeting_exclusion_count': len(prior),
        'fixed_meeting_ids': [m for t in TARGETS for m in t['meetings']],
        'prior_meeting_overlap_count': 0,
        'meeting_cap': MEETING_CAP,
        'target_venue_quotas': {t['venue']: t['quota'] for t in TARGETS},
        'selected_count': len(selected),
        'selected_by_venue': dict(sorted(venue_counts.items())),
        'selected_by_meeting': dict(sorted(meeting_counts.items())),
        'selected_unique_meeting_count': len(meeting_counts),
        'selected_unique_meetings_by_venue': {k: sorted(v) for k, v in sorted(venue_meetings.items())},
        'selected_by_exact_circumference': dict(sorted(Counter(str(x['exact_circumference_m']) for x in selected).items())),
        'selection_order': 'fixed venue order; fixed two meetings per venue; day 01/02/03/04 asc; race 01..12 asc; max 12 per meeting; fixed venue quotas',
        'aggregate_metric_warning': 'Venue-balanced confirmatory sample; overall aggregate is descriptive, not a population-frequency estimate.',
        'rejected_pre_only': rejected,
    }
    (OUT / 'SELECTION_AUDIT.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if len(selected) != 100:
        raise RuntimeError(f'coverage_balanced_v2_count_{len(selected)}_expected_100')

    GEN.write_text('race_id,url\n' + ''.join(f"{x['race_id']},{x['url']}\n" for x in selected), encoding='utf-8')
    return selected


if __name__ == '__main__':
    build_universe()
    v1.RACES = GEN
    v1.OUT = OUT
    v1.main()
