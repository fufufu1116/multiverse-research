#!/usr/bin/env python3
import csv,json,math,tempfile
from pathlib import Path
import subprocess,sys

FIELDS=['race_id','race_date','venue','race_no','car_no','rider_name_raw','class','style','competition_score','S','B','nige','makuri','sashi','mark','source_url','source_file_sha256','evidence_role']

def row(rid,date,venue,rno,car,name,cls,style,score):
    return [rid,date,venue,rno,car,name,cls,style,score,0,0,0,0,0,0,'https://keirin.kdreams.jp/x/racedetail/'+rid+'/','a'*64,'RETROSPECTIVE_PRE_DEVELOPMENT_ONLY_UNPROVEN_PIT']

with tempfile.TemporaryDirectory() as td:
    td=Path(td); pre=td/'pre.csv'; out=td/'out.json'
    rows=[]
    # race 1: non-girls, small gap, strong top1 -> selected
    scores=[100,94,93,92,91,90,89]
    for i,s in enumerate(scores,1): rows.append(row('0120260301010001','2026-03-01','TEST',1,i,f'R{i}','A1','追',s))
    # race 2: girls -> never selected even with dominant top1
    scores=[60,50,49,48,47,46,45]
    for i,s in enumerate(scores,1): rows.append(row('0120260301010002','2026-03-01','TEST',2,i,f'G{i}','L1','両',s))
    with pre.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f); w.writerow(FIELDS); w.writerows(rows)
    subprocess.run([sys.executable,'tools/keirin_nextgen5000_s0_preoutcome_materializer_v1.py','--pre-csv',str(pre),'--out',str(out)],check=True)
    x=json.loads(out.read_text(encoding='utf-8'))
    assert x['safeguards']['result_accessed'] is False
    assert x['safeguards']['payout_accessed'] is False
    assert x['summary']['races']==2
    assert x['summary']['girls_races']==1
    # race1 gap is 6, so frozen gap<3 must reject despite high top1
    assert x['races'][0]['top_score_gap']==6.0
    assert x['races'][0]['selected_by_frozen_rule'] is False
    assert x['races'][1]['girls'] is True
    assert x['races'][1]['selected_by_frozen_rule'] is False
    assert x['model']['beta']==0.22260435254784533
    print('PASS')
