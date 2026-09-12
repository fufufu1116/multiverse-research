from __future__ import annotations
import argparse, hashlib, json, math, zipfile
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

OUT=Path('v3/historical_all_market/research_candidates/new_lineage_stability_development_v2'); OUT.mkdir(parents=True,exist_ok=True)
PREREG='v3/historical_all_market/research_candidates/KEIRIN_NEW_LINEAGE_STABILITY_DEVELOPMENT_PROTOCOL_LOCK_20260913_v2.json'
NL1_FREEZE='v3/historical_all_market/research_candidates/KEIRIN_NEW_LINEAGE_MODEL_FREEZE_20260913_v1.json'
ZIP_SHA={
'b5':'882657a256f843876879f667b13342c9e5151c9afa84896e17addac9cfe1b925',
'b6':'fd0f320775efab8079d3fd076531fd7dc8ef2cae93ae207c3a125ca06222a91b',
'nl1val':'20029664c97dd5aaaf1e3ad3313a3f8cd9b714fd4ad2726650d852d4ba9b4aa4'
}
ALL=['score','win_rate','top2_rate','top3_rate','B','S']
CANDS={
'NL2_GEOBLEND_L2_3_V1':['nl1_minus_b1a_logprob'],
'NL2_GEOBLEND_REDUCED_L2_3_V1':['nl1_minus_b1a_logprob','score','win_rate','top3_rate'],
'NL2_GEOBLEND_NUMERIC_L2_3_V1':['nl1_minus_b1a_logprob']+ALL,
'NL2_B1A_NUMERIC_L2_3_V1':ALL,
}
L2=3.0

def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csha(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load_zip(p,k):
    if fsha(p)!=ZIP_SHA[k]: raise RuntimeError(k+'_artifact_sha_mismatch')
    with zipfile.ZipFile(p) as z:
        return [json.loads(z.read(n)) for n in ['PREDICTION_LOCK.json','SCORE.json','SELECTION_AUDIT.json']]
def z(v):
    a=np.array(v,float); s=float(a.std()); return (a-float(a.mean()))/(s if s else 1.0)
def nl1_probs(inputs,freeze):
    nums=freeze['numeric_features']; cls=freeze['class_levels']; sty=freeze['style_levels']; w=np.array(freeze['coefficients'],float)
    cols=[z([float(x[n]) for x in inputs]) for n in nums]
    X=np.column_stack(cols)
    if freeze['categorical_features']:
        if 'class' in freeze['categorical_features']:
            X=np.column_stack([X,np.array([[1.0 if str(x['class'])==q else 0.0 for q in cls] for x in inputs])])
        if 'style' in freeze['categorical_features']:
            X=np.column_stack([X,np.array([[1.0 if str(x['style'])==q else 0.0 for q in sty] for x in inputs])])
    s=X@w; p=np.exp(s-s.max()); p/=p.sum()
    return {int(x['car_no']):float(q) for x,q in zip(inputs,p)}

def dataset(p5,p6,pv,freeze):
    rows=[]; src={}
    for k,p in [('b5',p5),('b6',p6),('nl1val',pv)]:
        lock,score,sel=load_zip(p,k)
        wins={x['race_id']:int(x['winner_car']) for x in score['race_scores']}
        for r in lock['races']:
            b_rank=r.get('b1a_ranking',r.get('ranking'))
            bmap={int(x['car_no']):float(x['p_win']) for x in b_rank}
            nmap=nl1_probs(r['inputs'],freeze)
            rows.append({'batch':k,'race_id':str(r['race_id']),'meeting_id':str(r['meeting_id']),'inputs':r['inputs'],'b1a':bmap,'nl1':nmap,'winner':wins.get(r['race_id'])})
        src[k]={'zip_sha256':ZIP_SHA[k],'selected':int(lock['selected_count']),'scored':int(score['scored_count']),'result_failures':len(score.get('result_fetch_failures',[])),'prior_overlap':int(sel.get('prior_meeting_overlap_count',0))}
    ids=[r['race_id'] for r in rows]; dup=[x for x,n in Counter(ids).items() if n>1]
    lab=[r for r in rows if r['winner'] is not None]; meets=sorted({r['meeting_id'] for r in lab})
    if dup or len(rows)!=462 or len(lab)!=461 or len(meets)!=16: raise RuntimeError(f'dataset_gate_fail_{len(rows)}_{len(lab)}_{len(meets)}_{len(dup)}')
    fp=[{'race_id':r['race_id'],'meeting_id':r['meeting_id'],'winner':r['winner'],
         'inputs':[[int(x['car_no']),str(x['class']),str(x['style']),float(x['score']),float(x['S']),float(x['B']),float(x['win_rate']),float(x['top2_rate']),float(x['top3_rate'])] for x in r['inputs']],
         'b1a':sorted([[k,v] for k,v in r['b1a'].items()]),'nl1':sorted([[k,v] for k,v in r['nl1'].items()])}
        for r in sorted(rows,key=lambda x:x['race_id'])]
    audit={'record':'KEIRIN_NEW_LINEAGE_STABILITY_DEVELOPMENT_DATASET_AUDIT_v2','evidence_class':'EXPLORATORY_DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION',
           'preregistration':PREREG,'sources':src,'selected_or_retained_count':len(rows),'labelled_count':len(lab),
           'unlabelled_retained_race_ids':[r['race_id'] for r in rows if r['winner'] is None],
           'unique_race_ids':len(set(ids)),'unique_meetings':len(meets),'meeting_ids':meets,
           'labelled_by_meeting':dict(sorted(Counter(r['meeting_id'] for r in lab).items())),
           'development_dataset_sha256':csha(fp),'failed_nl1_validation_reclassified_as_exposed_development':True,
           'dev2000_used':False,'econ_holdout1000_used':False}
    return lab,audit

def design(r,features):
    inputs=r['inputs']; cars=np.array([int(x['car_no']) for x in inputs]); y=int(np.where(cars==int(r['winner']))[0][0])
    pb=np.array([max(r['b1a'][int(c)],1e-300) for c in cars],float)
    pn=np.array([max(r['nl1'][int(c)],1e-300) for c in cars],float)
    cols=[]
    for f in features:
        if f=='nl1_minus_b1a_logprob': cols.append(np.log(pn)-np.log(pb))
        else: cols.append(z([float(x[f]) for x in inputs]))
    X=np.column_stack(cols) if cols else np.zeros((len(inputs),0))
    return X,y,cars,np.log(pb)

def fit(train,features):
    pp=[design(r,features) for r in train]; d=pp[0][0].shape[1]
    def fg(w):
        loss=0.; g=np.zeros(d)
        for X,y,_,base in pp:
            s=base+X@w; p=np.exp(s-s.max()); p/=p.sum()
            loss-=math.log(max(float(p[y]),1e-300)); g+=X.T@p-X[y]
        loss/=len(pp); g/=len(pp)
        loss+=0.5*L2*np.mean(w*w); g+=L2*w/d
        return loss,g
    res=minimize(fg,np.zeros(d),method='L-BFGS-B',jac=True,options={'maxiter':2500,'ftol':1e-12})
    if not res.success: raise RuntimeError('optimizer_failed_'+str(res.message))
    return np.array(res.x,float),{'iterations':int(res.nit),'objective':float(res.fun),'coefficient_count':d}

def score_model(rs,w,features):
    out=[]
    for r in rs:
        X,y,cars,base=design(r,features); s=base+X@w; p=np.exp(s-s.max()); p/=p.sum()
        order=np.lexsort((cars,-p)); ranked=cars[order]; win=int(r['winner']); rank=int(np.where(ranked==win)[0][0]+1); pw=float(p[y])
        out.append({'race_id':r['race_id'],'meeting_id':r['meeting_id'],'rank':rank,'p':pw,'top1':rank==1,'top3':rank<=3,'ll':-math.log(max(pw,1e-300))})
    return out
def score_fixed(rs,key):
    out=[]
    for r in rs:
        probs=r[key]; q=sorted(probs.items(),key=lambda x:(-x[1],x[0])); win=int(r['winner'])
        rank=next(i+1 for i,(c,_) in enumerate(q) if c==win); pw=float(probs[win])
        out.append({'race_id':r['race_id'],'meeting_id':r['meeting_id'],'rank':rank,'p':pw,'top1':rank==1,'top3':rank<=3,'ll':-math.log(max(pw,1e-300))})
    return out
def met(a):
    n=len(a); return {'n':n,'top1_hits':sum(x['top1'] for x in a),'top1_accuracy':sum(x['top1'] for x in a)/n,
                      'winner_top3':sum(x['top3'] for x in a),'top3_rate':sum(x['top3'] for x in a)/n,
                      'mean_log_loss':sum(x['ll'] for x in a)/n}
def bymeet(a): return {m:met([x for x in a if x['meeting_id']==m]) for m in sorted({x['meeting_id'] for x in a})}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--batch5-zip',required=True); ap.add_argument('--batch6-zip',required=True); ap.add_argument('--nl1-validation-zip',required=True)
    a=ap.parse_args()
    freeze=json.loads(Path(NL1_FREEZE).read_text(encoding='utf-8'))
    if freeze['model_core_sha256']!='53608ed299e5148f215f1a199d897ac1d8320e04707ccb7453c67ced04080671': raise RuntimeError('nl1_freeze_sha_binding_fail')
    lab,audit=dataset(Path(a.batch5_zip),Path(a.batch6_zip),Path(a.nl1_validation_zip),freeze); meetings=audit['meeting_ids']
    b1=score_fixed(lab,'b1a'); n1=score_fixed(lab,'nl1'); bm=met(b1); nm=met(n1); bb=bymeet(b1); nb=bymeet(n1)
    reports={}; eligible=[]
    for cid,features in CANDS.items():
        held=[]; folds=[]
        for m in meetings:
            tr=[r for r in lab if r['meeting_id']!=m]; te=[r for r in lab if r['meeting_id']==m]
            w,fi=fit(tr,features); sc=score_model(te,w,features); held+=sc
            folds.append({'heldout_meeting':m,'train_races':len(tr),'test_races':len(te),'fit':fi,'metrics':met(sc)})
        om=met(held); mb=bymeet(held)
        imp=[m for m in meetings if mb[m]['mean_log_loss']<bb[m]['mean_log_loss']]
        lli=bm['mean_log_loss']-om['mean_log_loss']; t3d=om['top3_rate']-bm['top3_rate']; t1d=om['top1_accuracy']-bm['top1_accuracy']
        ok=lli>=0.02 and len(imp)>=10 and t3d>=-0.01 and t1d>=-0.01
        reports[cid]={'spec':{'features':features,'base_distribution':'log(B1a_probability)','l2_lambda':L2},
                      'overall_heldout':om,'by_meeting_heldout':mb,'folds':folds,
                      'pooled_log_loss_improvement_vs_b1a':lli,'top3_delta_vs_b1a':t3d,'top1_delta_vs_b1a':t1d,
                      'meetings_improved_vs_b1a':imp,'meetings_improved_count':len(imp),
                      'median_meeting_log_loss':float(np.median([mb[m]['mean_log_loss'] for m in meetings])),
                      'worst_meeting_log_loss':float(max(mb[m]['mean_log_loss'] for m in meetings)),
                      'eligible':ok}
        if ok: eligible.append(cid)
    if eligible:
        winner=sorted(eligible,key=lambda c:(reports[c]['overall_heldout']['mean_log_loss'],-reports[c]['meetings_improved_count'],reports[c]['worst_meeting_log_loss'],c))[0]
        features=CANDS[winner]; w,fi=fit(lab,features)
        core={'model_name':winner,'lineage':'NEW_LINEAGE_STABILITY_CORRECTION_v2','base_model':'B1a_RECONSTITUTED_v1',
              'base_predictor_blob':'62ae4ebc17cda47dca1fffae190fa44caae58ca3','base_temperature':1.15,
              'source_model_nl1_core_sha256':'53608ed299e5148f215f1a199d897ac1d8320e04707ccb7453c67ced04080671',
              'features':features,'numeric_transform':'within-race population z-score','probability':'softmax(log(p_B1a)+linear_correction)',
              'l2_lambda':L2,'coefficients':[float(x) for x in w],'fit_on_labelled_development_races':len(lab),
              'fit_on_meetings':meetings,'development_dataset_sha256':audit['development_dataset_sha256'],'preregistration':PREREG}
        mh=csha(core); freeze2={'record':'KEIRIN_NEW_LINEAGE_STABILITY_MODEL_FREEZE_v2','status':'FROZEN_AFTER_DEVELOPMENT_SELECTION_BEFORE_FRESH_UNTOUCHED_VALIDATION',
                                **core,'model_core_sha256':mh,'final_fit':fi,'fresh_validation_outcomes_accessed_for_this_model':False,
                                'failed_nl1_validation_used_only_as_declared_development':True,'dev2000_used':False,'econ_holdout1000_used':False,
                                'runtime':'OFF','automatic_betting':False}
        (OUT/'MODEL_FREEZE.json').write_text(json.dumps(freeze2,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        status='DEVELOPMENT_SEARCH_PASS_ELIGIBLE_STABILITY_CANDIDATE_SELECTED'
    else:
        winner=None; mh=None; status='FAIL_DEVELOPMENT_SEARCH_NO_CANDIDATE'
    report={'record':'KEIRIN_NEW_LINEAGE_STABILITY_DEVELOPMENT_SCORE_v2','status':status,'evidence_class':'EXPLORATORY_DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION',
            'preregistration':PREREG,'dataset_audit':audit,
            'baseline_b1a':{'overall':bm,'by_meeting':bb},
            'failed_nl1_reference':{'overall':nm,'by_meeting':nb,'status':'REFERENCE_ONLY_FAILED_PRIOR_UNTOUCHED_VALIDATION'},
            'candidates':reports,'eligible_candidates':eligible,'selected_candidate':winner,'selected_model_core_sha256':mh,
            'selection_rule_applied_exactly':True,'fresh_future_validation_outcomes_used':False,'dev2000_used':False,'econ_holdout1000_used':False,
            'runtime':'OFF','automatic_betting':False}
    (OUT/'DATASET_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'SCORE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NL2_DEVELOPMENT_SUMMARY='+json.dumps({'status':status,'dataset':{k:audit[k] for k in ['selected_or_retained_count','labelled_count','unique_meetings','development_dataset_sha256']},
      'b1a':bm,'nl1_reference':nm,'candidates':{c:{'overall':x['overall_heldout'],'ll_improvement':x['pooled_log_loss_improvement_vs_b1a'],
      'meetings_improved_count':x['meetings_improved_count'],'top1_delta':x['top1_delta_vs_b1a'],'top3_delta':x['top3_delta_vs_b1a'],'eligible':x['eligible']} for c,x in reports.items()},
      'selected_candidate':winner,'selected_model_core_sha256':mh},ensure_ascii=False))
if __name__=='__main__': main()
