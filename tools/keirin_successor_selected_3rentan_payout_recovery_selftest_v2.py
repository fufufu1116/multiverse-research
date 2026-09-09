#!/usr/bin/env python3
"""Selftest v2 for successor selected 3rentan complete-settlement parser."""
from importlib.util import spec_from_file_location,module_from_spec
import json

spec=spec_from_file_location("m","tools/keirin_successor_selected_3rentan_payout_recovery_v2.py")
m=module_from_spec(spec);spec.loader.exec_module(m)

def html(cell):
    return f"""<html><head><title>Test競輪 2026年 7月 1日 1R</title></head><body>
<table>
<tr><th>2枠連</th><td>x</td><td>x</td><th>2車連</th><td>x</td><td>x</td><th>3連勝</th><td>x</td><td>x</td><th>ワイド</th><td>x</td></tr>
<tr><td>x</td><td>x</td><td>x</td><td>1-2 300円(1)</td><td>x</td><td>{cell}</td></tr>
</table></body></html>""".encode('utf-8')

url='https://keirin.kdreams.jp/test/racedetail/9920260701010001/'
r=m.parse(html('1-2-3 1,230円(4)'),url,'2026-07-01')
s=json.loads(r['winning_3rentan_settlements_json'])
assert s==[{'payout_yen_per_100':1230,'popularity_raw':'4','ticket':'1-2-3'}],s
assert len(r['source_file_sha256'])==64,r

r2=m.parse(html('1-6-4 250円(2) 1-6-5 440円(4)'),url,'2026-07-01')
s2=json.loads(r2['winning_3rentan_settlements_json'])
assert s2==[
 {'payout_yen_per_100':250,'popularity_raw':'2','ticket':'1-6-4'},
 {'payout_yen_per_100':440,'popularity_raw':'4','ticket':'1-6-5'}
],s2
print('PASS_SUCCESSOR_3RENTAN_COMPLETE_SETTLEMENT_SELFTEST',s,s2)
