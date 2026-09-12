from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # noqa: F401; installs hardened result parser

# Exact authoritative circumferences already used by the active research lane.
v1.CIRC.update({'maebashi': 335.0, 'kawasaki': 400.0})

SEED = Path('.github/workflows/races.csv')
TEMP = Path('.github/workflows/races_temporal_replication_100_v1.csv')
BATCH3_AUDIT = Path('v3/historical_all_market/research_candidates/KEIRIN_INDEPENDENT_MEETING_REPLICATION_100_B1A_COMPLETE_AUDIT_20260913_v1.json')
GEN = Path('.github/workflows/races_coverage_balanced_independent_meeting_100_v1.csv')
OUT = Path('v3/historical_all_market/research_candidates/virtualworld_coverage_balanced_independent_meeting_100_b1a_v1')
OUT.mkdir(parents=True, exist_ok=True)

START = date(2026, 6, 1)
END = date(2026, 7, 31)
MEETING_CAP = 12
TARGETS = [
    ('12', 'aomori', 17),
    ('21', 'yahiko', 17),
    ('22', 'maebashi', 17),
    ('34', 'kawasaki', 17),
    ('43', 'gifu', 16),
    ('46', 'toyama', 16),
]


def meeting_from_url(url: str) -> str:
    p = urlparse(url).path.strip('/').split('/')
    return p[-4]


def read_meetings(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {meeting_from_url(x['url']) for x in csv.DictReader(path.read_text(encoding='utf-8').splitlines())}


def prior_meetings() -> set[str]:
    out = read_meetings(SEED) | read_meetings(TEMP)
    if not BATCH3_AUDIT.exists():
        raise RuntimeError('batch3_audit_missing_fail_closed')
    audit = json.loads(BATCH3_AUDIT.read_text(encoding='utf-8'))
    for x in audit.get('selection', {}).get('selected_meetings', []):
        out.add(str(x['meeting_id']))
    return out


def race_url(meeting: str, di: str, rr: int) -> str:
    day = f'{meeting}{di}00'
    return f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{rr:02d}/3rentan/'


def parse_probe(meeting: str, venue: str, di: str, rr: int):
    rid = f'CBAL_{meeting}_{venue}_{di}_{rr:02d}R'
    url = race_url(meeting, di, rr)
    payload = v1.fetch(url)
    rows, parsed_venue, circ = v1.parse_pre(rid, url, payload)
    if parsed_venue != venue:
        raise RuntimeError(f'venue_mismatch_{parsed_venue}_{venue}')
    return rid, url, circ, rows


def meeting_exists_precomplete(meeting: str, venue: str) -> bool:
    # Bounded PRE-only meeting discovery. Result/payout pages are never touched here.
    for rr in range(1, 13):
        try:
            parse_probe(meeting, venue, '01', rr)
            return True
        except Exception:
            pass
    return False


def build_universe():
    excluded = prior_meetings()
    selected: list[dict] = []
    rejected_pre_only: list[dict] = []
    venue_counts = Counter()
    meeting_counts = Counter()
    venue_meetings: dict[str, set[str]] = defaultdict(set)
    discovery_probe_dates = Counter()

    for code, venue, quota in TARGETS:
        d = START
        while d <= END and venue_counts[venue] < quota:
            meeting = f'{code}{d.strftime("%Y%m%d")}'
            d += timedelta(days=1)
            if meeting in excluded:
                continue
            discovery_probe_dates[venue] += 1
            if not meeting_exists_precomplete(meeting, venue):
                continue

            for di in ('01', '02', '03'):
                for rr in range(1, 13):
                    if venue_counts[venue] >= quota or meeting_counts[meeting] >= MEETING_CAP:
                        break
                    try:
                        rid, url, circ, _rows = parse_probe(meeting, venue, di, rr)
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
                        rejected_pre_only.append({
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
        if len(venue_meetings[venue]) < 2:
            raise RuntimeError(f'venue_meeting_diversity_failed_{venue}_{len(venue_meetings[venue])}_expected_at_least_2')

    overlap = [x for x in selected if x['meeting_id'] in excluded]
    audit = {
        'record': 'KEIRIN_COVERAGE_BALANCED_INDEPENDENT_MEETING_100_SELECTION_EXECUTION_v1',
        'date_window': {'start': START.isoformat(), 'end': END.isoformat()},
        'result_access_during_selection': False,
        'payout_access_during_selection': False,
        'prior_meeting_exclusion_count': len(excluded),
        'meeting_cap': MEETING_CAP,
        'target_venue_quotas': {venue: quota for _code, venue, quota in TARGETS},
        'selected_count': len(selected),
        'selected_by_venue': dict(sorted(venue_counts.items())),
        'selected_unique_meeting_count': len(meeting_counts),
        'selected_unique_meetings_by_venue': {k: sorted(v) for k, v in sorted(venue_meetings.items())},
        'selected_by_meeting': dict(sorted(meeting_counts.items())),
        'selected_by_exact_circumference': dict(sorted(Counter(str(x['exact_circumference_m']) for x in selected).items())),
        'prior_meeting_overlap_count': len(overlap),
        'discovery_probe_date_count_by_venue': dict(sorted(discovery_probe_dates.items())),
        'selection_order': 'fixed venue order; date asc; eligible meeting only; day 01/02/03 asc; race 01..12 asc; max 12 selected per meeting; fixed venue quotas',
        'aggregate_metric_warning': 'Venue-stratified confirmatory sample; overall aggregate is not population-representative.',
        'rejected_pre_only': rejected_pre_only,
    }
    (OUT / 'SELECTION_AUDIT.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if len(selected) != 100:
        raise RuntimeError(f'coverage_balanced_complete_pre_count_{len(selected)}_expected_100')
    if overlap:
        raise RuntimeError('prior_meeting_overlap_detected')

    GEN.write_text('race_id,url\n' + ''.join(f"{x['race_id']},{x['url']}\n" for x in selected), encoding='utf-8')
    return selected


if __name__ == '__main__':
    build_universe()
    v1.RACES = GEN
    v1.OUT = OUT
    v1.main()
