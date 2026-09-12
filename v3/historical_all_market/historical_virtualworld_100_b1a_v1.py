from __future__ import annotations
import csv, json, math, re, time
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
import requests
from bs4 import BeautifulSoup

RACES=Path('.github/workflows/races.csv')
OUT=Path('v3/historical_all_market/research_candidates/virtualworld_100_b1a_v1')
OUT.mkdir(parents=True,exist_ok=True)
MODEL='B1a_RECONSTITUTED_v1'
BLOB='62ae4ebc17cda47dca1fffae190fa44caae58ca3'
TEMP=1.15
W={'score':.55,'win_rate':.18,'top2_rate':.12,'top3_rate':.08,'B':.04,'S':.03}
BETA={'A1':0.10862511799550383,'A2':-0.10862511799550574,'A3':4.991005121158697e-16,'L1':-1.446593378458555e-16,'S1':-0.12658801568020364,'S2':-0.9504993423499002,'SS':1.0770873580301035,'両':0.10822708520060681,'追':-0.3773237125550861,'逃':0.26909662735448}
CIRC={'aomori':400.0,'yahiko':400.0,'gifu':400.0,'toyama':333.3,'matsuyama':400.0,'takeo':400.0,'kumamoto':400.0}
UA={'User-Agent':'Mozilla/5.0 MultiverseResearch-HistoricalVirtualWorld100/1.0','Accept-Language':'ja,en-US;q=0.7,en;q=0.5'}
s=requests.Session(); s.headers.update(UA)

def txt(n): return re.sub(r'\s+',' ',n.get_text(' ',strip=True)).strip() if n else ''
def num(x):
    x=x.replace(',','').replace('%','').strip()
    return float(x) if re.fullmatch(r'-?\d+(?:\.\d+)?',x) else None

def fetch(url):
    last=None
    for a in range(3):
        try:
            r=s.get(url,timeout=45); last=r
            if r.status_code==200 and r.content: return r.content
        except Exception:
            if a==2: raise
        time.sleep(1.0+a)
    raise RuntimeError(f'HTTP {getattr(last,"status_code",None)} {url}')

def parse_pre(rid,url,payload):
    soup=BeautifulSoup(payload,'lxml')
    tab=None
    for t in soup.find_all('table'):
        z=txt(t)
        if '直近4ヶ月' in z and '競走得点' in z and ('2連対率' in z or '2連 対率' in z) and ('3連対率' in z or '3連 対率' in z):
            tab=t; break
    if tab is None: raise RuntimeError('entrant_table_missing')
    rows=[]
    for tr in tab.find_all('tr'):
        cs=[txt(c) for c in tr.find_all(['td','th'])]
        pidx=next((i for i,c in enumerate(cs) if re.search(r'/\d{1,2}/\d{2,3}$',c.replace(' ',''))),None)
        if pidx is None: continue
        before=cs[max(0,pidx-3):pidx]
        cars=[int(x) for c in before for x in re.findall(r'(?<!\d)([1-9])(?!\d)',c)]
        if not cars: continue
        car=cars[-1]
        klass=next((c.strip() for c in cs if re.fullmatch(r'(?:A[123]|S[12]|SS|L1)',c.strip())),None)
        style=next((c.strip() for c in cs if c.strip() in {'逃','両','追'}),None)
        after=cs[pidx+1:]
        if len(after)<17: continue
        vals=[num(x) for x in after[3:17]]
        if any(v is None for v in vals): continue
        score=vals[0]; S,B,nige,makuri,sashi,mark,w1,w2,w3,out,wr,t2,t3=vals[1:]
        if klass is None or style is None: continue
        rows.append({'race_id':rid,'car_no':car,'class':klass,'style':style,'score':score,'S':S,'B':B,'win_rate':wr,'top2_rate':t2,'top3_rate':t3})
    by={r['car_no']:r for r in rows}; rows=[by[k] for k in sorted(by)]
    if not 5<=len(rows)<=9: raise RuntimeError(f'entrant_count_{len(rows)}')
    venue=rid.split('_')[2]
    if venue not in CIRC: raise RuntimeError(f'unknown_circumference_{venue}')
    return rows,venue,CIRC[venue]

def zvals(vals):
    a=np.array(vals,dtype=float); sd=a.std()
    return (a-a.mean())/(sd if sd else 1.0)

def predict(rows):
    zs={k:zvals([r[k] for r in rows]) for k in W}
    scores=[]
    for i,r in enumerate(rows):
        x=sum(W[k]*zs[k][i] for k in W)/TEMP + BETA[r['class']] + BETA[r['style']]
        scores.append(x)
    a=np.array(scores); p=np.exp(a-a.max()); p=p/p.sum()
    out=[]
    for r,q in zip(rows,p): out.append({'car_no':r['car_no'],'p_win':float(q),'class':r['class'],'style':r['style']})
    return sorted(out,key=lambda x:(-x['p_win'],x['car_no']))

def result_url(rid,base):
    parts=urlparse(base).path.strip('/').split('/')
    # .../odds/<meeting>/<day>/<race>/3rentan
    day=parts[-3]; rr=parts[-2]
    venue=rid.split('_')[2]
    return f'https://keirin.kdreams.jp/{venue}/racedetail/{day}{rr}/?pageType=showResult'

def parse_winner(payload):
    soup=BeautifulSoup(payload,'lxml')
    for t in soup.find_all('table'):
        if '着順' not in txt(t) or '車番' not in txt(t): continue
        for tr in t.find_all('tr'):
            cs=[txt(c) for c in tr.find_all(['td','th'])]
            ints=[]
            for c in cs:
                if re.fullmatch(r'[1-9]',c): ints.append(int(c))
            if len(ints)>=2 and ints[0]==1: return ints[1]
    raise RuntimeError('winner_not_found')

def main():
    universe=list(csv.DictReader(RACES.read_text(encoding='utf-8').splitlines()))
    if len(universe)!=100: raise RuntimeError(f'universe_count_{len(universe)}')
    frozen=[]; exclusions=[]
    for x in universe:
        try:
            payload=fetch(x['url']); rows,venue,circ=parse_pre(x['race_id'],x['url'],payload); pred=predict(rows)
            frozen.append({'race_id':x['race_id'],'source_url':x['url'],'venue':venue,'circumference_m':circ,'inputs':rows,'ranking':pred})
        except Exception as e: exclusions.append({'race_id':x['race_id'],'reason':str(e)})
    lock={'record':'KEIRIN_HISTORICAL_VIRTUALWORLD_100_B1A_PREDICTION_LOCK_v1','evidence_class':'RETROSPECTIVE_KR015','model':MODEL,'predictor_blob':BLOB,'temperature':TEMP,'universe_count':100,'frozen_count':len(frozen),'excluded_before_result_fetch':exclusions,'result_access_before_lock':False,'payout_access':False,'races':frozen}
    (OUT/'PREDICTION_LOCK.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    scored=[]; result_fail=[]
    for r in frozen:
        try:
            winner=parse_winner(fetch(result_url(r['race_id'],r['source_url'])))
            rank=next(i+1 for i,q in enumerate(r['ranking']) if q['car_no']==winner)
            pw=next(q['p_win'] for q in r['ranking'] if q['car_no']==winner)
            scored.append({'race_id':r['race_id'],'venue':r['venue'],'circumference_m':r['circumference_m'],'winner_car':winner,'winner_rank':rank,'winner_probability':pw,'top1_hit':rank==1,'top3_hit':rank<=3,'log_loss':-math.log(max(pw,1e-15))})
        except Exception as e: result_fail.append({'race_id':r['race_id'],'reason':str(e)})
    def metrics(a):
        n=len(a)
        return {'n':n,'top1_hits':sum(x['top1_hit'] for x in a),'top1_accuracy':sum(x['top1_hit'] for x in a)/n if n else None,'winner_top3':sum(x['top3_hit'] for x in a),'top3_rate':sum(x['top3_hit'] for x in a)/n if n else None,'mean_log_loss':sum(x['log_loss'] for x in a)/n if n else None}
    bycirc={}
    for c in sorted({x['circumference_m'] for x in scored}): bycirc[str(c)]=metrics([x for x in scored if x['circumference_m']==c])
    byvenue={}
    for v in sorted({x['venue'] for x in scored}): byvenue[v]=metrics([x for x in scored if x['venue']==v])
    report={'record':'KEIRIN_HISTORICAL_VIRTUALWORLD_100_B1A_SCORE_v1','status':'COMPLETE' if len(scored)==len(frozen) else 'PARTIAL_RESULT_FETCH_FAIL_CLOSED','evidence_class':'RETROSPECTIVE_KR015','integrity':'PRE fields parsed and B1a predictions locked before dedicated result-page fetch in this run; historical source pages may themselves be outcome-bearing, therefore never upgraded above retrospective','model':MODEL,'predictor_blob':BLOB,'universe_count':100,'frozen_before_results':len(frozen),'pre_exclusions':exclusions,'scored_count':len(scored),'result_fetch_failures':result_fail,'overall':metrics(scored),'by_exact_circumference':bycirc,'by_venue':byvenue,'race_scores':scored,'odds_used':False,'retune':False,'post_result_deletion':False}
    (OUT/'SCORE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('VIRTUALWORLD100_SUMMARY='+json.dumps({k:report[k] for k in ['status','universe_count','frozen_before_results','scored_count','overall','by_exact_circumference','by_venue']},ensure_ascii=False))

if __name__=='__main__': main()
