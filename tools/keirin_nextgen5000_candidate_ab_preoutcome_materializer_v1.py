#!/usr/bin/env python3
"""Outcome-blind Candidate_A + B1a_RECONSTITUTED_v1 materializer for NEXTGEN5000.

Consumes only corrected PRE v2 CSV fields and exactly recovered frozen DEV2000
model constants. No result, payout, odds, forecast or comment input is accepted.
"""
from __future__ import annotations
import argparse,csv,itertools,json,math
from collections import defaultdict
from pathlib import Path

TEMP=1.15
COEF={'score':.55,'win_rate':.18,'quinella_rate':.12,'trio_rate':.08,'B':.04,'S':.03}
BETA={
 'style_逃':0.26909662735448,'style_追':-0.3773237125550861,'style_両':0.10822708520060681,
 'class_SS':1.0770873580301035,'class_S1':-0.12658801568020364,'class_S2':-0.9504993423499002,
 'class_A1':0.10862511799550383,'class_A2':-0.10862511799550574,
 'class_A3':4.991005121158697e-16,'class_L1':-1.446593378458555e-16
}
STYLES={'逃','追','両'}
CLASSES={'SS','S1','S2','A1','A2','A3','L1'}
FORBIDDEN={'result','finish','payout','settlement','odds','forecast','prediction','tips','comment','narabiyoso','roi','ev'}
REQUIRED={
 'race_id','race_date','venue','race_no','car_no','rider_name_raw','class','style',
 'gear_ratio','competition_score','S','B','win_rate','quinella_rate','trio_rate',
 'source_file_sha256','evidence_role'
}
RULE_ID='NON_GIRLS_GAP_LT3_CONF40_TOP3_3RENHUKU_1PT_NO_PRICE_FILTER'

def softmax(xs):
    m=max(xs); ex=[math.exp(x-m) for x in xs]; s=sum(ex)
    return [x/s for x in ex]

def zscores(vals):
    mu=sum(vals)/len(vals)
    var=sum((x-mu)**2 for x in vals)/len(vals)
    sd=math.sqrt(var) or 1.0
    return [(x-mu)/sd for x in vals]

def three_fuku_prob(pmap,cars3):
    target=tuple(sorted(cars3))
    total=0.0
    for i,j,k in itertools.permutations(target,3):
        pi=pmap[i]
        d2=1.0-pi
        if d2<=0: raise ValueError('FAIL-CLOSED:PL_d2')
        pj=pmap[j]/d2
        d3=1.0-pmap[i]-pmap[j]
        if d3<=0: raise ValueError('FAIL-CLOSED:PL_d3')
        pk=pmap[k]/d3
        total += pi*pj*pk
    return total

def materialize_race(rows):
    rows=sorted(rows,key=lambda r:int(r['car_no']))
    cars=[int(r['car_no']) for r in rows]
    if cars!=list(range(1,max(cars)+1)): raise ValueError('FAIL-CLOSED:car_continuity')
    src={r['source_file_sha256'] for r in rows}
    if len(src)!=1: raise ValueError('FAIL-CLOSED:mixed_source_hash')
    for r in rows:
        if r['style'] not in STYLES or r['class'] not in CLASSES:
            raise ValueError(f"FAIL-CLOSED:category:{r['style']}/{r['class']}")

    raw={
      'score':[float(r['competition_score']) for r in rows],
      'win_rate':[float(r['win_rate']) for r in rows],
      'quinella_rate':[float(r['quinella_rate']) for r in rows],
      'trio_rate':[float(r['trio_rate']) for r in rows],
      'B':[float(r['B']) for r in rows],
      'S':[float(r['S']) for r in rows]
    }
    zz={k:zscores(v) for k,v in raw.items()}
    base=[]
    for i,r in enumerate(rows):
        s=sum(COEF[k]*zz[k][i] for k in COEF)/TEMP
        base.append(s)
    pa=softmax(base)
    b1log=[]
    for i,r in enumerate(rows):
        b1log.append(base[i]+BETA['style_'+r['style']]+BETA['class_'+r['class']])
    pb=softmax(b1log)

    pamap={cars[i]:pa[i] for i in range(len(cars))}
    pbmap={cars[i]:pb[i] for i in range(len(cars))}
    a_top=max(cars,key=lambda c:(pamap[c],-c))
    b_top=max(cars,key=lambda c:(pbmap[c],-c))
    conservative={c:min(pamap[c],pbmap[c]) for c in cars}
    rank=sorted(cars,key=lambda c:(-conservative[c],c))
    top1=rank[0]; top3=rank[:3]
    gap=sorted(raw['score'],reverse=True)[0]-sorted(raw['score'],reverse=True)[1]
    girls=all(r['class']=='L1' for r in rows)
    agree=a_top==b_top
    conf=conservative[top1]
    selected=(not girls) and gap<3.0 and agree and conf>=0.40
    ticket='='.join(map(str,sorted(top3)))
    p3a=three_fuku_prob(pamap,top3)
    p3b=three_fuku_prob(pbmap,top3)

    riders=[]
    for i,r in enumerate(rows):
        riders.append({
          'car_no':cars[i],'rider_name_raw':r['rider_name_raw'],'class':r['class'],'style':r['style'],
          'competition_score':raw['score'][i],
          'candidate_a_logit':base[i],'candidate_a_win_probability':pa[i],
          'b1a_logit':b1log[i],'b1a_win_probability':pb[i],
          'conservative_win_probability':conservative[cars[i]]
        })
    return {
      'race_id':rows[0]['race_id'],'race_date':rows[0]['race_date'],'venue':rows[0]['venue'],
      'race_no':int(rows[0]['race_no']),'rider_count':len(rows),'girls':girls,
      'top_score_gap':gap,'candidate_a_top1_car':a_top,'b1a_top1_car':b_top,
      'top1_agree':agree,'conservative_rank':rank,'conservative_top1_car':top1,
      'conservative_top1_probability':conf,'conservative_top3_cars':top3,
      'ticket_3renhuku':ticket,
      'candidate_a_ticket_probability':p3a,'b1a_ticket_probability':p3b,
      'conservative_ticket_probability':min(p3a,p3b),
      'selected_by_frozen_rule':selected,'source_file_sha256':next(iter(src)),
      'riders':riders
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pre-csv',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    with open(a.pre_csv,encoding='utf-8',newline='') as f:
        rd=csv.DictReader(f)
        fields=set(rd.fieldnames or [])
        bad=FORBIDDEN & {x.lower() for x in fields}
        if bad: raise SystemExit(f'FAIL-CLOSED:forbidden_columns:{sorted(bad)}')
        miss=REQUIRED-fields
        if miss: raise SystemExit(f'FAIL-CLOSED:missing_columns:{sorted(miss)}')
        rows=list(rd)
    if not rows: raise SystemExit('FAIL-CLOSED:no_rows')

    by=defaultdict(list)
    for r in rows: by[r['race_id']].append(r)
    races=[]
    rejects=[]
    for rid in sorted(by,key=lambda x:(by[x][0]['race_date'],x)):
        try: races.append(materialize_race(by[rid]))
        except Exception as e: rejects.append({'race_id':rid,'reason':str(e)})
    if len(races)<int(.95*len(by)):
        raise SystemExit(f'FAIL-CLOSED:too_many_materialization_rejects accepted={len(races)} total={len(by)}')

    payload={
      'record':'KEIRIN_NEXTGEN5000_CANDIDATE_A_B1A_PREOUTCOME_MATERIALIZATION_v1',
      'status':'PRE_ONLY_PREDICTION_AND_SELECTION_FROZEN_NO_OUTCOME_ACCESS',
      'model_freeze':'KEIRIN_CANDIDATE_A_B1A_RECONSTITUTED_V1_REPRODUCTION_FREEZE_20260909_v1',
      'rule_id':RULE_ID,
      'summary':{
        'input_races':len(by),'materialized_races':len(races),'rejected_races':len(rejects),
        'rider_rows':sum(r['rider_count'] for r in races),'girls_races':sum(r['girls'] for r in races),
        'top1_agreement_races':sum(r['top1_agree'] for r in races),
        'conf40_agreement_races':sum(r['top1_agree'] and r['conservative_top1_probability']>=.40 for r in races),
        'selected_races':sum(r['selected_by_frozen_rule'] for r in races)
      },
      'rejects':rejects,
      'races':races,
      'safeguards':{
        'result_accessed':False,'payout_accessed':False,'odds_accessed':False,
        'forecast_or_comment_accessed':False,'model_refit':False,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False
      }
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload['summary'],ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
