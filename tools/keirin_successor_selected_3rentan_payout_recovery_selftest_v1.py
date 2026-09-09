#!/usr/bin/env python3
"""Selftest for successor selected 3rentan payout parser."""
from importlib.util import spec_from_file_location,module_from_spec

spec=spec_from_file_location("m","tools/keirin_successor_selected_3rentan_payout_recovery_v1.py")
m=module_from_spec(spec);spec.loader.exec_module(m)

html=b"""<html><head><title>Test競輪 2026年 7月 1日 1R</title></head><body>
<table>
<tr><th>2枠連</th><td>x</td><td>x</td><th>2車連</th><td>x</td><td>x</td><th>3連勝</th><td>x</td><td>x</td><th>ワイド</th><td>x</td></tr>
<tr><td>x</td><td>x</td><td>x</td><td>1-2 300円(1人気)</td><td>x</td><td>1-2-3 1,230円(4人気)</td></tr>
</table>
</body></html>"""
url='https://keirin.kdreams.jp/test/racedetail/9920260701010001/'
r=m.parse(html,url,'2026-07-01')
assert r['race_id']=='9920260701010001',r
assert r['winning_3rentan_ticket']=='1-2-3',r
assert r['payout_yen_per_100']==1230,r
assert len(r['source_file_sha256'])==64,r
assert r['evidence_role']==m.ROLE,r
print('PASS_SUCCESSOR_3RENTAN_PAYOUT_PARSER_SELFTEST',r)
