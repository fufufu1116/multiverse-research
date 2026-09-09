#!/usr/bin/env python3
"""Deterministic process-quarantine filter for NEXTGEN5000 outcome labels."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

QUARANTINE={'8320260327010001'}
FIELDS=['race_id','race_date','venue','race_no','finish_1','finish_2','finish_3','source_url','source_file_sha256','evidence_role']

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',action='append',required=True)
    ap.add_argument('--out',required=True)
    ap.add_argument('--receipt',required=True)
    a=ap.parse_args()
    rows=[]; dropped=[]
    seen=set()
    for p in a.input:
        with open(p,encoding='utf-8',newline='') as f:
            rd=csv.DictReader(f)
            if set(rd.fieldnames or [])!=set(FIELDS):
                raise SystemExit(f'FAIL-CLOSED:unexpected_fields:{p}')
            for r in rd:
                rid=r['race_id']
                if rid in seen: raise SystemExit(f'FAIL-CLOSED:duplicate:{rid}')
                seen.add(rid)
                if rid in QUARANTINE: dropped.append(r); continue
                rows.append(r)
    rows.sort(key=lambda r:(r['race_date'],r['race_id']))
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    rec={
      'record':'KEIRIN_NEXTGEN5000_PRIMARY_OUTCOME_QUARANTINE_FILTER_RECEIPT_v1',
      'fixed_quarantine':sorted(QUARANTINE),
      'input_rows':len(rows)+len(dropped),'output_rows':len(rows),'dropped_rows':len(dropped),
      'dropped_race_ids':[r['race_id'] for r in dropped],
      'reason':'single process-exposed race; exclusion fixed before primary outcome collection',
      'model_or_threshold_change':False
    }
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rec,ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
