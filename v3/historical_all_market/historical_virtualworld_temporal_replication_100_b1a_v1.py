from __future__ import annotations
import csv, json, re
from pathlib import Path
from urllib.parse import urlparse
import historical_virtualworld_100_b1a_v1 as v1
import historical_virtualworld_100_b1a_v2 as v2  # installs hardened result parser

v1.CIRC.update({'maebashi':335.0,'kawasaki':400.0})
SEED=Path('.github/workflows/races.csv')
GEN=Path('.github/workflows/races_temporal_replication_100_v1.csv')
OUT=Path('v3/historical_all_market/research_candidates/virtualworld_temporal_replication_100_b1a_v1')
OUT.mkdir(parents=True,exist_ok=True)
VENUE_BY_CODE={'12':'aomori','21':'yahiko','22':'maebashi','34':'kawasaki','43':'gifu','46':'toyama','75':'matsuyama','84':'takeo','87':'kumamoto'}

def parts(url):
    p=urlparse(url).path.strip('/').split('/')
    return p[-4],p[-3],p[-2]

def build_universe():
    seed=list(csv.DictReader(SEED.read_text(encoding='utf-8').splitlines()))
    seed_urls={x['url'] for x in seed}
    meetings={}
    for x in seed:
        meeting,day,race=parts(x['url'])
        code=meeting[:2]
        venue=VENUE_BY_CODE.get(code)
        if venue is None: continue
        meetings.setdefault((meeting,venue),set()).add(day[-4:-2])
    candidates=[]
    for (meeting,venue),used_days in sorted(meetings.items()):
        base_day=meeting
        for di in ('01','02','03'):
            if di in used_days: continue
            day=f'{base_day}{di}00'
            for rr in range(1,13):
                url=f'https://keirin.kdreams.jp/gamboo/keirin-kaisai/race-card/odds/{meeting}/{day}/{rr:02d}/3rentan/'
                if url in seed_urls: continue
                rid=f'TEMP_{meeting}_{venue}_{di}_{rr:02d}R'
                candidates.append((rid,url))
    selected=[]; rejected=[]
    for rid,url in candidates:
        if len(selected)>=100: break
        try:
            payload=v1.fetch(url)
            rows,venue,circ=v1.parse_pre(rid,url,payload)
            selected.append({'race_id':rid,'url':url})
        except Exception as e:
            rejected.append({'race_id':rid,'url':url,'reason':str(e)})
    audit={
      'record':'KEIRIN_TEMPORAL_REPLICATION_100_SELECTION_EXECUTION_v1',
      'result_access_during_selection':False,'payout_access_during_selection':False,
      'candidate_count':len(candidates),'selected_count':len(selected),'rejected_pre_only':rejected,
      'selection_order':'meeting_id asc, alternate day 01/02/03 asc, race 01..12; first 100 complete PRE parses',
      'seed_exact_url_overlap':sum(1 for x in selected if x['url'] in seed_urls)
    }
    (OUT/'SELECTION_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if len(selected)!=100:
        raise RuntimeError(f'temporal_replication_complete_pre_count_{len(selected)}_expected_100')
    GEN.write_text('race_id,url\n'+''.join(f"{x['race_id']},{x['url']}\n" for x in selected),encoding='utf-8')
    return selected

if __name__=='__main__':
    build_universe()
    v1.RACES=GEN
    v1.OUT=OUT
    v1.main()
