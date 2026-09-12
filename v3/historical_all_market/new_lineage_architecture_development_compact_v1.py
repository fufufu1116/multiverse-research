from __future__ import annotations
import argparse, hashlib, json, math, zipfile
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

OUT=Path('v3/historical_all_market/research_candidates/new_lineage_architecture_development_v1'); OUT.mkdir(parents=True,exist_ok=True)
PREREG='v3/historical_all_market/research_candidates/KEIRIN_NEW_LINEAGE_ARCHITECTURE_DEVELOPMENT_PREREGISTRATION_20260913_v1.json'
ZIP_SHA={'b5':'882657a256f843876879f667b13342c9e5151c9afa84896e17addac9cfe1b925','b6':'fd0f320775efab8079d3fd076531fd7dc8ef2cae93ae207c3a125ca06222a91b'}
CLS=['A1','A2','A3','L1','S1','S2','SS']; STY=['逃','追','両']; ALL=['score','win_rate','top2_rate','top3_rate','B','S']
CANDS={
'NL1_REDUCED_L2_V1':(['score','win_rate','top3_rate'],[]),
'NL1_NUMERIC_L2_V1':(ALL,[]),
'NL1_NUMERIC_CLASS_STYLE_L2_V1':(ALL,['class','style']),
'NL1_SCORE_ONLY_L2_V1':(['score'],[]),
}

def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csha(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(p,k):
    if fsha(p)!=ZIP_SHA[k]: raise RuntimeError(k+'_artifact_sha_mismatch')
    with zipfile.ZipFile(p) as z: return [json.loads(z.read(n)) for n in ['PREDICTION_LOCK.json','SCORE.json','SELECTION_AUDIT.json']]
def dataset(p5,p6):
    rr=[]; src={}
    for k,p in [('b5',p5),('b6',p6)]:
        lock,score,sel=load(p,k); wins={x['race_id']:int(x['winner_car']) for x in score['race_scores']}
        for r in lock['races']:
            rr.append({'batch':k,'race_id':str(r['race_id']),'meeting_id':str(r['meeting_id']),'inputs':r['inputs'],'b1a':r['ranking'],'winner':wins.get(r['race_id'])})
        src[k]={'zip_sha256':ZIP_SHA[k],'selected':int(lock['selected_count']),'scored':int(score['scored_count']),'result_failures':len(score.get('result_fetch_failures',[])),'prior_overlap':int(sel.get('prior_meeting_overlap_count',0))}
    ids=[r['race_id'] for r in rr]; dup=[x for x,n in Counter(ids).items() if n>1]
    lab=[r for r in rr if r['winner'] is not None]; meets=sorted({r['meeting_id'] for r in lab})
    if dup or len(rr)!=321 or len(lab)!=320 or len(meets)!=11: raise RuntimeError(f'dataset_gate_fail_{len(rr)}_{len(lab)}_{len(meets)}_{len(dup)}')
    fp=[{'race_id':r['race_id'],'meeting_id':r['meeting_id'],'winner':r['winner'],'inputs':[[int(x['car_no']),str(x['class']),str(x['style']),float(x['score']),float(x['S']),float(x['B']),float(x['win_rate']),float(x['top2_rate']),float(x['top3_rate'])] for x in r['inputs']]} for r in sorted(rr,key=lambda x:x['race_id'])]
    audit={'record':'KEIRIN_NEW_LINEAGE_DEVELOPMENT_DATASET_AUDIT_v1','evidence_class':'DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION','preregistration':PREREG,'sources':src,'selected_count':len(rr),'labelled_count':len(lab),'unlabelled_retained_race_ids':[r['race_id'] for r in rr if r['winner'] is None],'unique_race_ids':len(set(ids)),'unique_meetings':len(meets),'meeting_ids':meets,'labelled_by_meeting':dict(sorted(Counter(r['meeting_id'] for r in lab).items())),'development_dataset_sha256':csha(fp),'protected_evidence_used':False,'dev2000_used':False,'econ_holdout1000_used':False}
    return lab,audit

def z(v):
    a=np.array(v,float); s=float(a.std()); return (a-float(a.mean()))/(s if s else 1.0)
def design(r,nums,cats):
    rows=r['inputs']; cols=[z([float(x[n]) for x in rows]) for n in nums]; X=np.column_stack(cols) if cols else np.zeros((len(rows),0))
    if 'class' in cats: X=np.column_stack([X,np.array([[1.0 if str(x['class'])==q else 0.0 for q in CLS] for x in rows])])
    if 'style' in cats: X=np.column_stack([X,np.array([[1.0 if str(x['style'])==q else 0.0 for q in STY] for x in rows])])
    cars=np.array([int(x['car_no']) for x in rows]); y=int(np.where(cars==int(r['winner']))[0][0]); return X,y,cars
def fit(train,nums,cats):
    pp=[design(r,nums,cats) for r in train]; d=pp[0][0].shape[1]
    def fg(w):
        loss=0.; g=np.zeros(d)
        for X,y,_ in pp:
            s=X@w; p=np.exp(s-s.max()); p/=p.sum(); loss-=math.log(max(float(p[y]),1e-300)); g+=X.T@p-X[y]
        loss/=len(pp); g/=len(pp); loss+=0.5*np.mean(w*w); g+=w/d; return loss,g
    res=minimize(fg,np.zeros(d),method='L-BFGS-B',jac=True,options={'maxiter':2000,'ftol':1e-12})
    if not res.success: raise RuntimeError('optimizer_failed_'+str(res.message))
    return np.array(res.x,float),{'iterations':int(res.nit),'objective':float(res.fun),'coefficient_count':d}
def score(rs,w,nums,cats):
    out=[]
    for r in rs:
        X,y,cars=design(r,nums,cats); s=X@w; p=np.exp(s-s.max()); p/=p.sum(); order=np.lexsort((cars,-p)); ranked=cars[order]; win=int(r['winner']); rank=int(np.where(ranked==win)[0][0]+1); pw=float(p[y]); out.append({'race_id':r['race_id'],'meeting_id':r['meeting_id'],'rank':rank,'p':pw,'top1':rank==1,'top3':rank<=3,'ll':-math.log(max(pw,1e-300))})
    return out
def b1a(rs):
    out=[]
    for r in rs:
        q=sorted(r['b1a'],key=lambda x:(-float(x['p_win']),int(x['car_no']))); win=int(r['winner']); rank=next(i+1 for i,x in enumerate(q) if int(x['car_no'])==win); pw=next(float(x['p_win']) for x in q if int(x['car_no'])==win); out.append({'race_id':r['race_id'],'meeting_id':r['meeting_id'],'rank':rank,'p':pw,'top1':rank==1,'top3':rank<=3,'ll':-math.log(max(pw,1e-300))})
    return out
def met(a):
    n=len(a); return {'n':n,'top1_hits':sum(x['top1'] for x in a),'top1_accuracy':sum(x['top1'] for x in a)/n,'winner_top3':sum(x['top3'] for x in a),'top3_rate':sum(x['top3'] for x in a)/n,'mean_log_loss':sum(x['ll'] for x in a)/n}
def bymeet(a): return {m:met([x for x in a if x['meeting_id']==m]) for m in sorted({x['meeting_id'] for x in a})}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--batch5-zip',required=True); ap.add_argument('--batch6-zip',required=True); a=ap.parse_args(); lab,audit=dataset(Path(a.batch5_zip),Path(a.batch6_zip)); meetings=audit['meeting_ids']
    br=b1a(lab); bm=met(br); bb=bymeet(br); reports={}; eligible=[]
    for cid,(nums,cats) in CANDS.items():
        held=[]; folds=[]
        for m in meetings:
            tr=[r for r in lab if r['meeting_id']!=m]; te=[r for r in lab if r['meeting_id']==m]; w,fi=fit(tr,nums,cats); sc=score(te,w,nums,cats); held+=sc; folds.append({'heldout_meeting':m,'train_races':len(tr),'test_races':len(te),'fit':fi,'metrics':met(sc)})
        om=met(held); mb=bymeet(held); imp=[m for m in meetings if mb[m]['mean_log_loss']<bb[m]['mean_log_loss']]; lli=bm['mean_log_loss']-om['mean_log_loss']; t3d=om['top3_rate']-bm['top3_rate']; ok=lli>=0.015 and len(imp)>=6 and t3d>=-0.02
        reports[cid]={'spec':{'numeric_features':nums,'categorical_features':cats,'l2_lambda':1.0},'overall_heldout':om,'by_meeting_heldout':mb,'folds':folds,'pooled_log_loss_improvement_vs_b1a':lli,'top3_delta_vs_b1a':t3d,'meetings_improved_vs_b1a':imp,'meetings_improved_count':len(imp),'median_meeting_log_loss':float(np.median([mb[m]['mean_log_loss'] for m in meetings])),'worst_meeting_log_loss':float(max(mb[m]['mean_log_loss'] for m in meetings)),'eligible':ok}
        if ok: eligible.append(cid)
    if eligible:
        winner=sorted(eligible,key=lambda c:(reports[c]['overall_heldout']['mean_log_loss'],-reports[c]['meetings_improved_count'],-reports[c]['overall_heldout']['top1_accuracy'],c))[0]; nums,cats=CANDS[winner]; w,fi=fit(lab,nums,cats); names=list(nums)+([f'class={x}' for x in CLS] if 'class' in cats else [])+([f'style={x}' for x in STY] if 'style' in cats else []); core={'model_name':winner,'lineage':'NEW_LINEAGE_DEVELOPMENT_ONLY_v1','feature_names':names,'numeric_features':nums,'categorical_features':cats,'class_levels':CLS if 'class' in cats else [],'style_levels':STY if 'style' in cats else [],'numeric_transform':'within-race population z-score','probability':'within-race softmax(linear score)','l2_lambda':1.0,'coefficients':[float(x) for x in w],'fit_on_labelled_development_races':len(lab),'fit_on_meetings':meetings,'development_dataset_sha256':audit['development_dataset_sha256'],'preregistration':PREREG}; mh=csha(core); freeze={'record':'KEIRIN_NEW_LINEAGE_MODEL_FREEZE_v1','status':'FROZEN_AFTER_DEVELOPMENT_SELECTION_BEFORE_UNTOUCHED_VALIDATION',**core,'model_core_sha256':mh,'final_fit':fi,'validation_outcomes_accessed_for_this_model':False,'runtime':'OFF','automatic_betting':False}; (OUT/'MODEL_FREEZE.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); status='DEVELOPMENT_SEARCH_PASS_ELIGIBLE_REPLACEMENT_SELECTED'
    else: winner=None; mh=None; status='DEVELOPMENT_SEARCH_FAIL_NO_ELIGIBLE_REPLACEMENT'
    report={'record':'KEIRIN_NEW_LINEAGE_ARCHITECTURE_DEVELOPMENT_SCORE_v1','status':status,'evidence_class':'DEVELOPMENT_ONLY_NOT_UNTOUCHED_VALIDATION','preregistration':PREREG,'dataset_audit':audit,'baseline_b1a':{'model':'B1a_RECONSTITUTED_v1','predictor_blob':'62ae4ebc17cda47dca1fffae190fa44caae58ca3','overall':bm,'by_meeting':bb},'candidates':reports,'eligible_candidates':eligible,'selected_candidate':winner,'selected_model_core_sha256':mh,'selection_rule_applied_exactly':True,'fresh_validation_outcomes_used':False,'dev2000_used':False,'econ_holdout1000_used':False,'runtime':'OFF','automatic_betting':False}; (OUT/'DATASET_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (OUT/'SCORE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print('NEW_LINEAGE_DEVELOPMENT_SUMMARY='+json.dumps({'status':status,'dataset':{k:audit[k] for k in ['selected_count','labelled_count','unique_meetings','development_dataset_sha256']},'baseline':bm,'candidates':{c:{'overall':x['overall_heldout'],'ll_improvement':x['pooled_log_loss_improvement_vs_b1a'],'meetings_improved_count':x['meetings_improved_count'],'eligible':x['eligible']} for c,x in reports.items()},'selected_candidate':winner,'selected_model_core_sha256':mh},ensure_ascii=False))
if __name__=='__main__': main()
