from __future__ import annotations

"""Technical endpoint fix for NL2 economics validation v1.

Scientific/preregistered semantics are unchanged. The failed first execution attempted to
parse confirmed closing prices from the PRE race-card/odds page. The canonical Kdreams
price and settlement parsers are explicitly built for the historical racedetail
?pageType=showResult payload. This wrapper only corrects that source endpoint.

The prior failed run stopped before any development settlement parser invocation and
before any validation target fetch, so the preregistered validation set remains untouched.
"""

from collections import Counter

import historical_virtualworld_nl2_economics_validation_v1 as v1


def corrected_showresult_url(r: dict) -> str:
    return v1.b1a.result_url(r['race_id'], r['source_url'])


def collect_pre_price_fixed(targets: list[dict], rule: dict, configs: list[dict], phase: str, nl1: dict, nl2: dict):
    frozen = []
    rejected = []
    for target in targets:
        v1.b1a.CIRC[str(target['venue'])] = float(target['circumference_m'])
        for day in range(1, 5):
            for race_no in range(1, 13):
                try:
                    r = v1.nl2val.freeze_race(target, day, race_no, nl1, nl2)
                    price_url = corrected_showresult_url(r)
                    payload = v1.b1a.fetch(price_url)
                    p = v1.price_parser.parse_payload(payload)
                    choices = v1.ticket_choices(r, p, rule, configs)
                    frozen.append({
                        'phase': phase,
                        'race_id': r['race_id'],
                        'source_url': r['source_url'],
                        'price_source_url': price_url,
                        'meeting_id': r['meeting_id'],
                        'meeting_day_index': r['meeting_day_index'],
                        'race_no': r['race_no'],
                        'venue': r['venue'],
                        'circumference_m': r['circumference_m'],
                        'active_car_numbers': p['active_car_numbers'],
                        'sold_markets': p['sold_markets'],
                        'price_raw_sha256': p['raw_sha256'],
                        'price_parser_output_contains_result_fields': False,
                        'historical_price_source_page_may_be_outcome_bearing': True,
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


def fetch_settlements_fixed(races: list[dict]):
    out = {}
    failures = []
    for r in races:
        try:
            settlement_url = corrected_showresult_url(r)
            payload = v1.b1a.fetch(settlement_url)
            s = v1.settlement_parser.parse_payload(payload)
            out[r['race_id']] = s
        except Exception as e:
            failures.append({'race_id': r['race_id'], 'meeting_id': r['meeting_id'], 'reason': str(e)})
    return out, failures


v1.collect_pre_price = collect_pre_price_fixed
v1.fetch_settlements = fetch_settlements_fixed

if __name__ == '__main__':
    v1.main()
