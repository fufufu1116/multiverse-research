from __future__ import annotations
import csv, json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse
import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # installs hardened result parser

v1.CIRC.update({'maebashi':335.0,'kawasaki':400.0})
SEED=Path('.github/workflows/races.csv')
TEMP=Path('.github/workflows/races_temporal_replication_100_v1.csv')
GEN=Path('.github/workflows/races_independent_meeting_replication_100_v1.csv')
OUT=Path('v3/historical_all_market/research_candidates/virtualworld_independent_meeting_replication_100_b1a_v1')
OUT.mkdir(parents=True,exist_ok=True)
VENUE_BY_CODE={'12':'aomori','21':'yahiko','22':'maebashi','34':'kawasaki','43':'gifu','46':'toyama','75':'matsuyama','84':'takeo','87':'kumamoto'}
START=date(2026,7,1)
END=date(2026,7,31)

def meeting_from_url(url):
    p=urlparse(url).path.strip('/').split('/')
    return p[-4]

def read_meetings(path):
    if not path.exists():
        return set()
    return {meeting_from_url(x['url']) for x in csv.DictReader(path.read_text(encoding='utf-8').splitlines())}

def build_universe():
    excluded=read_meetings(SEED)|read_meetings(TEMP)
    candidates=[]
    d=START
    while d<=END:
        ymd=d.strftime('%Y%m%d')
        for code,venue in sorted(VENUE_BY_CODE.items()):
            meeting=f'{code}{ymd}'
            if meeting in excluded:
                continue
            for di in ('01','02','03'):
                day=f'{meeting}{di}00'
                for rr in range(1,13):
                    url=f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{rr:02d}/3rentan/'
                    rid=f'IND_{meeting}_{venue}_{di}_{rr:02d}R'
                    candidates.append((rid,url,meeting,venue,di,rr))
        d+=timedelta(days=1)

    selected=[]; rejected=[]
    selected_meetings=set()
    for rid,url,meeting,venue,di,rr in candidates:
        if len(selected)>=100:
            break
        try:
            payload=v1.fetch(url)
            rows,parsed_venue,circ=v1.parse_pre(rid,url,payload)
            selected.append({'race_id':rid,'url':url,'meeting_id':meeting,'venue':parsed_venue,'exact_circumference_m':circ})
            selected_meetings.add(meeting)
        except Exception as e:
            rejected.append({'race_id':rid,'url':url,'meeting_id':meeting,'reason':str(e)})

    audit={
      'record':'KEIRIN_INDEPENDENT_MEETING_REPLICATION_100_SELECTION_EXECUTION_v1',
      'date_window':{'start':START.isoformat(),'end':END.isoformat()},
      'result_access_during_selection':False,
      'payout_access_during_selection':False,
      'excluded_prior_meeting_count':len(excluded),
      'candidate_count':len(candidates),
      'selected_count':len(selected),
      'selected_unique_meeting_count':len(selected_meetings),
      'prior_meeting_overlap_count':sum(1 for x in selected if x['meeting_id'] in excluded),
      'selection_order':'date asc, venue code asc, day 01/02/03, race 01..12; first 100 complete PRE parses',
      'rejected_pre_only':rejected
    }
    (OUT/'SELECTION_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if len(selected)!=100:
        raise RuntimeError(f'independent_meeting_complete_pre_count_{len(selected)}_expected_100')
    if audit['prior_meeting_overlap_count']!=0:
        raise RuntimeError('independent_meeting_overlap_detected')
    GEN.write_text('race_id,url\n'+''.join(f"{x['race_id']},{x['url']}\n" for x in selected),encoding='utf-8')
    return selected

if __name__=='__main__':
    build_universe()
    v1.RACES=GEN
    v1.OUT=OUT
    v1.main()
