#!/usr/bin/env python3
"""Frozen Stage-7 DEV2000 A/B/C economic evaluation after authorized Settlement."""
from __future__ import annotations
import argparse, importlib.util, json, traceback
from datetime import datetime, timezone
from pathlib import Path
import stage7_eval_core_v1 as c

AUDIT="a0360b1c5622b0664e8180186a40eca9827fc63e"
CORE_BLOB="4787faee7259b0c40733ee9bba84e7909eeae51f"
STAGE456_BLOB="a0ed6984969b0b98af1b074ef9fd2348f16604a0"
APPROVAL_BLOB="71e87740ded33ea73c3f534d39830080ad8b43bb"
SETTLEMENT_PARSER_BLOB="b8b8ab0e0904541bd6fc45e7fe415d323e63ec45"
GOV={
 "STAGE3_TICKET_FILTER_FAMILY_PREREG_v1.md":"ba4175bb044bcacfa66a7b8d089e92c04762b2e6",
 "STAGE4_CONSENSUS_AGREEMENT_GATE_PREREG_v1.md":"f5bb38e97dd2543842308f9b8ee401957d2e5216",
 "STAGE5_PORTFOLIO_TEMPLATE_PREREG_v1.md":"f13b5aa5584d260d30032c269cfc205a312f2426",
 "STAGE6_BANKROLL_RISK_POLICY_PREREG_v1.md":"7dc0ac09440755ad1c43959237c0d975be11b245",
 "STAGE7_TIME_SPLIT_SELECTION_VALIDATION_PREREG_v1.md":"0cb70520777d4ac9d00ddd90b888df1f403c3a7e",
 "STAGE7_EXECUTION_CONVENTIONS_FREEZE_v1.md":"b388ef5622d4c92ae4df96ad0105882b4994adf4",
}

def now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def bind_stage456(repo):
 p=repo/"v3/historical_all_market/stage456_preoutcome_decision_engine_v1.py"
 if not p.is_file() or c.git_blob(p)!=STAGE456_BLOB:raise c.FailClosed("Stage456 blob")
 s=importlib.util.spec_from_file_location("s456",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def verify_gov(repo):
 d=repo/"v3/historical_all_market/governance";obs={}
 for n,h in GOV.items():
  p=d/n
  if not p.is_file() or c.git_blob(p)!=h:raise c.FailClosed(f"governance blob {n}")
  obs[n]=h
 p=d/"INDEPENDENT_GOVERNANCE_STAGE7_SETTLEMENT_APPROVE_RECEIPT_v1.json"
 if not p.is_file() or c.git_blob(p)!=APPROVAL_BLOB:raise c.FailClosed("approval blob")
 x=c.load_json(p);dec=x.get("explicit_decisions",{})
 if x.get("verdict")!="APPROVE" or x.get("audit_snapshot_commit")!=AUDIT or dec.get("FINITE_784_CONFIGURATION_SEARCH_AND_SELECTION")!="ACCEPTABLE" or dec.get("DEV2000_SETTLEMENT_BULK")!="AUTHORIZED_FOR_FROZEN_STAGE7_ONLY" or dec.get("ECON_HOLDOUT1000")!="SEALED":raise c.FailClosed("approval content")
 obs[p.name]=APPROVAL_BLOB;return obs

def paths(my):
 o=my/"MULTIVERSE_ALL_MARKET_STAGE7_SETTLEMENT_EVAL_v1";s=o/"SETTLEMENT_ONLY"
 return o,{"state":o/"STAGE7_EXECUTION_STATE_v1.json","A":o/"STAGE7_A_ALL784_METRICS_v1.csv","top":o/"STAGE7_A_TOP10_FREEZE_v1.json","B":o/"STAGE7_B_VALIDATION_METRICS_v1.csv","freeze":o/"FINAL_DEV2000_CONFIGURATION_FREEZE_v1.json","ledger":o/"STAGE7_C_RACE_LEDGER_v1.csv","blog":o/"STAGE7_BOOTSTRAP_BATCH_LOG_v1.txt","C":o/"STAGE7_SEGMENT_C_OOS_RECEIPT_v1.json","final":o/"STAGE7_FINAL_EXECUTION_RECEIPT_v1.json","fatal":o/"STAGE7_EVALUATION_FATAL_v1.json","sr":o/"STAGE7_SETTLEMENT_BULK_RECEIPT_v1.json","sA":s/"DEV2000_SETTLEMENT_A_v1.jsonl","sB":s/"DEV2000_SETTLEMENT_B_v1.jsonl","sC":s/"DEV2000_SETTLEMENT_C_UNTOUCHED_v1.jsonl"}
def state(p,phase,**kw):c.dump_json(p,{"record":"STAGE7_EXECUTION_STATE_v1","phase":phase,"updated_at_utc":now(),"ECON_HOLDOUT1000":"SEALED",**kw})

def load_freeze(p,allc,gov,seg):
 x=c.load_json(p);cid=str(x.get("configuration_id",""))
 if x.get("record")!="FINAL_DEV2000_CONFIGURATION_FREEZE_v1" or x.get("status")!="FROZEN_BEFORE_SEGMENT_C_OPEN" or cid not in allc or x.get("audit_snapshot_commit")!=AUDIT or x.get("governance_blobs")!=gov or x.get("stage7_eval_core_git_blob")!=CORE_BLOB or x.get("stage456_git_blob")!=STAGE456_BLOB or x.get("stage2_sha256")!=c.EXPECTED_STAGE2_SHA256 or x.get("prediction_sha256")!=c.EXPECTED_PRED_SHA256 or x.get("universe_sha256")!=c.EXPECTED_UNIVERSE_SHA256 or x.get("settlement_segment_sha256")!=seg or x.get("ECON_HOLDOUT1000")!="SEALED":raise c.FailClosed("final freeze binding")
 if not isinstance(x.get("A_TOP10"),list) or not x["A_TOP10"] or int(x.get("B_pass_count",0))<=0:raise c.FailClosed("final freeze selection")
 return x,c.sha256_file(p)

def run(a):
 my=Path(a.mydrive);repo=Path(a.repo_root).resolve();out,p=paths(my);out.mkdir(parents=True,exist_ok=True)
 if p["final"].is_file():
  f=c.load_json(p["final"])
  if f.get("status") in {"PASS_COMPLETE","HALT_NO_A_ELIGIBLE_CONFIGURATION","HALT_NO_B_VALIDATED_CONFIGURATION"}:print(f"[ALREADY FINAL] {f['status']} — no rescore",flush=True);return 0
  raise c.FailClosed("unknown final status")
 corep=repo/"v3/historical_all_market/stage7_eval_core_v1.py"
 if not corep.is_file() or c.git_blob(corep)!=CORE_BLOB:raise c.FailClosed("Stage7 core blob")
 gov=verify_gov(repo);m=bind_stage456(repo)
 if len(m.PROFILES)*len(m.GATES)*len(m.TEMPLATES)*len(m.STAKE_POLICIES)!=784:raise c.FailClosed("config count")
 u=my/"MULTIVERSE_DEV2000_UNIVERSE_RECOVERY/DEV2000_UNIVERSE_v1.csv";s2=my/"MULTIVERSE_ALL_MARKET_STAGE2_PRICE_EV_v1/DEV2000_ALL_MARKET_PRICE_EV_CATALOG_v1.jsonl";pr=my/"MULTIVERSE_DEV2000_PREDICTION_LOCK_v3_IPHONE_LITE/DEV2000_CANDIDATE_A_B1A_RECONSTITUTED_v1_PREDICTIONS.csv"
 bi=c.build_universe(u);uids=set(bi.values());pred=c.load_prediction(pr,uids);idx=c.Stage2Index.build(s2,uids)
 if not p["sr"].is_file():raise c.FailClosed("settlement bulk receipt missing")
 sr=c.load_json(p["sr"]);seg=sr.get("segment_sha256",{})
 if sr.get("status")!="PASS_COMPLETE" or sr.get("audit_snapshot_commit")!=AUDIT or sr.get("settlement_parser_git_blob")!=SETTLEMENT_PARSER_BLOB or sr.get("stage7_approval_git_blob")!=APPROVAL_BLOB or sr.get("scientific_trial_count_before_open")!=0 or sr.get("ECON_HOLDOUT1000")!="SEALED" or set(seg)!={"A","B","C"}:raise c.FailClosed("settlement receipt")
 allc=[c.config_id(x[0],g[0],t,s) for x in m.PROFILES for g in m.GATES for t in m.TEMPLATES for s in m.STAKE_POLICIES]
 if len(allc)!=784 or len(set(allc))!=784:raise c.FailClosed("config IDs")
 Cids=[bi[i] for i in range(1501,2001)]
 def finish(cr,fr,fh):
  cid=fr["configuration_id"]
  if cr.get("record")!="STAGE7_SEGMENT_C_OOS_RECEIPT_v1" or cr.get("status")!="PASS_COMPLETE" or cr.get("configuration_id")!=cid or cr.get("final_configuration_freeze_sha256")!=fh or cr.get("segment_c_scoring_count")!=1 or cr.get("ECON_HOLDOUT1000")!="SEALED":raise c.FailClosed("C receipt")
  if c.sha256_file(p["ledger"])!=cr.get("c_race_ledger_sha256") or c.sha256_file(p["blog"])!=cr.get("bootstrap_batch_log_sha256"):raise c.FailClosed("C artifact hash")
  final={"record":"STAGE7_FINAL_EXECUTION_RECEIPT_v1","status":"PASS_COMPLETE","completed_at_utc":now(),"audit_snapshot_commit":AUDIT,"governance_blobs":gov,"stage7_eval_core_git_blob":CORE_BLOB,"stage456_git_blob":STAGE456_BLOB,"stage2_sha256":c.EXPECTED_STAGE2_SHA256,"prediction_sha256":c.EXPECTED_PRED_SHA256,"universe_sha256":c.EXPECTED_UNIVERSE_SHA256,"settlement_segment_sha256":seg,"A_TOP10":fr["A_TOP10"],"B_pass_count":fr["B_pass_count"],"FINAL_DEV2000_CONFIGURATION":cid,"final_configuration_freeze_sha256":fh,"segment_c_oos_receipt_sha256":c.sha256_file(p["C"]),"segment_c_verdict":cr["verdict"],"segment_c_scoring_count":1,"technical_resume_same_frozen_trial":bool(cr.get("technical_resume_same_frozen_trial",False)),"technical_resume_count":int(cr.get("technical_resume_count",0)),"stage7_realized_scientific_trial_count":1,"post_outcome_rule_tuning":False,"rescue_tuning":False,"model_refit":False,"live_wagering":False,"ECON_HOLDOUT1000":"SEALED"}
  c.dump_json(p["final"],final);state(p["state"],"C_COMPLETE",final_configuration_id=cid,final_configuration_freeze_sha256=fh,final_receipt_sha256=c.sha256_file(p["final"]),segment_c_accessed=True,segment_c_scoring_count=1,technical_resume_count=final["technical_resume_count"])
  if p["fatal"].exists():p["fatal"].unlink()
  print(json.dumps(final,ensure_ascii=False,indent=2),flush=True);print(json.dumps(cr,ensure_ascii=False,indent=2),flush=True);return 0
 if p["freeze"].is_file():
  fr,fh=load_freeze(p["freeze"],allc,gov,seg);cid=fr["configuration_id"];st=c.load_json(p["state"]) if p["state"].is_file() else {};phase=str(st.get("phase",""));rc=int(st.get("technical_resume_count",0) or 0);print(f"[RESUME BOUNDARY] {cid} phase={phase or 'STATE_MISSING'}",flush=True)
  if p["C"].is_file():print("[RESUME] C receipt complete — NO C RESCORE",flush=True);return finish(c.load_json(p["C"]),fr,fh)
  if p["ledger"].is_file():
   led,cs=c.load_c_ledger(p["ledger"],Cids);rc+=1;state(p["state"],"C_OPEN_STARTED",final_configuration_id=cid,final_configuration_freeze_sha256=fh,segment_c_accessed=True,segment_c_scoring_count=1,technical_resume_count=rc,technical_resume_same_frozen_trial=True,resume_mode="BOOTSTRAP_FROM_COMPLETE_C_LEDGER_NO_RESCORE");print("[RESUME] C ledger complete — bootstrap only",flush=True);boot=c.bootstrap(led,p["blog"]);v=c.verdict(cs,boot);cr={"record":"STAGE7_SEGMENT_C_OOS_RECEIPT_v1","status":"PASS_COMPLETE","verdict":v,"configuration_id":cid,"final_configuration_freeze_sha256":fh,"C_metrics":c.metrics(cid,cs,"C_UNTOUCHED_TEST"),"bootstrap":boot,"c_race_ledger_sha256":c.sha256_file(p["ledger"]),"bootstrap_batch_log_sha256":c.sha256_file(p["blog"]),"segment_c_scoring_count":1,"technical_resume_same_frozen_trial":True,"technical_resume_count":rc,"rescue_tuning_performed":False,"model_refit":False,"ECON_HOLDOUT1000":"SEALED"};c.dump_json(p["C"],cr);return finish(cr,fr,fh)
  if phase=="C_COMPLETE":raise c.FailClosed("C_COMPLETE without C artifacts")
  tr=phase=="C_OPEN_STARTED";rc+=int(tr)
 else:
  if p["state"].is_file() and c.load_json(p["state"]).get("phase") in {"FINAL_CONFIG_FROZEN","C_OPEN_STARTED","C_COMPLETE"}:raise c.FailClosed("C state without freeze")
  A=c.load_settlement(p["sA"],"A",1000,str(seg["A"]));Ai=[bi[i] for i in range(1,1001)];AS,_=c.evaluate("A",Ai,A,allc,idx,pred,m);c.write_metrics(p["A"],[c.metrics(x,AS[x],"A_DEVELOPMENT") for x in allc]);elig=c.sort_states([(x,s) for x,s in AS.items() if s.bet_races>=100 and s.total_stake>0 and s.min_bankroll>=0 and c.dd_leq(s,35)]);top=[x for x,_ in elig[:10]];at={"record":"STAGE7_A_TOP10_FREEZE_v1","status":"PASS" if top else "NO_A_ELIGIBLE_CONFIGURATION","eligible_count":len(elig),"A_TOP10":top,"ranking":[c.metrics(x,s,"A_DEVELOPMENT") for x,s in elig[:10]],"a_metrics_sha256":c.sha256_file(p["A"]),"configuration_id_format":"PROFILE:GATE:TEMPLATE:STAKE_POLICY","segment_starting_bankroll_jpy":c.INITIAL_BANKROLL,"segment_c_accessed":False,"ECON_HOLDOUT1000":"SEALED"};c.dump_json(p["top"],at);state(p["state"],"A_COMPLETE",A_TOP10_sha256=c.sha256_file(p["top"]),segment_c_accessed=False,technical_resume_count=0);print(f"[A FREEZE] eligible={len(elig)} top10={top}",flush=True)
  if not top:
   f={"record":"STAGE7_FINAL_EXECUTION_RECEIPT_v1","status":"HALT_NO_A_ELIGIBLE_CONFIGURATION","audit_snapshot_commit":AUDIT,"segment_c_accessed":False,"a_top10_sha256":c.sha256_file(p["top"]),"stage7_realized_scientific_trial_count":1,"ECON_HOLDOUT1000":"SEALED","model_refit":False,"post_outcome_rule_tuning":False,"live_wagering":False};c.dump_json(p["final"],f);return 0
  B=c.load_settlement(p["sB"],"B",500,str(seg["B"]));Bi=[bi[i] for i in range(1001,1501)];BS,_=c.evaluate("B",Bi,B,top,idx,pred,m);c.write_metrics(p["B"],[c.metrics(x,BS[x],"B_VALIDATION") for x in top]);bp=c.sort_states([(x,s) for x,s in BS.items() if s.total_return>s.total_stake and s.bet_races>=50 and s.min_bankroll>=0 and c.dd_leq(s,35)])
  if not bp:
   f={"record":"STAGE7_FINAL_EXECUTION_RECEIPT_v1","status":"HALT_NO_B_VALIDATED_CONFIGURATION","audit_snapshot_commit":AUDIT,"segment_c_accessed":False,"a_top10_sha256":c.sha256_file(p["top"]),"b_metrics_sha256":c.sha256_file(p["B"]),"stage7_realized_scientific_trial_count":1,"ECON_HOLDOUT1000":"SEALED","model_refit":False,"post_outcome_rule_tuning":False,"live_wagering":False};state(p["state"],"B_COMPLETE_NO_PASS",segment_c_accessed=False,technical_resume_count=0);c.dump_json(p["final"],f);return 0
  cid,bs=bp[0];fr={"record":"FINAL_DEV2000_CONFIGURATION_FREEZE_v1","status":"FROZEN_BEFORE_SEGMENT_C_OPEN","configuration_id":cid,"configuration":dict(zip(("stage3_profile","stage4_gate","stage5_template","stage6_stake_policy"),c.parse_config(cid))),"selection_source":"A_TOP10 then B pass/rank exactly per Stage7 prereg","B_metrics":c.metrics(cid,bs,"B_VALIDATION"),"B_pass_count":len(bp),"A_TOP10":top,"a_top10_sha256":c.sha256_file(p["top"]),"b_metrics_sha256":c.sha256_file(p["B"]),"segment_starting_bankroll_jpy":c.INITIAL_BANKROLL,"segment_c_accessed_at_freeze":False,"audit_snapshot_commit":AUDIT,"governance_blobs":gov,"stage7_eval_core_git_blob":CORE_BLOB,"stage456_git_blob":STAGE456_BLOB,"stage2_sha256":c.EXPECTED_STAGE2_SHA256,"prediction_sha256":c.EXPECTED_PRED_SHA256,"universe_sha256":c.EXPECTED_UNIVERSE_SHA256,"settlement_segment_sha256":seg,"frozen_at_utc":now(),"ECON_HOLDOUT1000":"SEALED"};c.dump_json(p["freeze"],fr);fh=c.sha256_file(p["freeze"]);state(p["state"],"FINAL_CONFIG_FROZEN",final_configuration_id=cid,final_configuration_freeze_sha256=fh,segment_c_accessed=False,technical_resume_count=0);print(f"[FINAL CONFIG FROZEN BEFORE C OPEN] {cid} sha={fh}",flush=True);tr=False;rc=0
 state(p["state"],"C_OPEN_STARTED",final_configuration_id=cid,final_configuration_freeze_sha256=fh,segment_c_accessed=True,segment_c_scoring_count=1,technical_resume_count=rc,technical_resume_same_frozen_trial=tr);C=c.load_settlement(p["sC"],"C",500,str(seg["C"]));CS,led=c.evaluate("C",Cids,C,[cid],idx,pred,m,ledger_for=cid);cs=CS[cid];c.write_c_ledger(p["ledger"],led);boot=c.bootstrap(led,p["blog"]);v=c.verdict(cs,boot);cr={"record":"STAGE7_SEGMENT_C_OOS_RECEIPT_v1","status":"PASS_COMPLETE","verdict":v,"configuration_id":cid,"final_configuration_freeze_sha256":fh,"C_metrics":c.metrics(cid,cs,"C_UNTOUCHED_TEST"),"bootstrap":boot,"c_race_ledger_sha256":c.sha256_file(p["ledger"]),"bootstrap_batch_log_sha256":c.sha256_file(p["blog"]),"segment_c_scoring_count":1,"technical_resume_same_frozen_trial":tr,"technical_resume_count":rc,"rescue_tuning_performed":False,"model_refit":False,"ECON_HOLDOUT1000":"SEALED"};c.dump_json(p["C"],cr);return finish(cr,fr,fh)
def main():
 a=argparse.ArgumentParser();a.add_argument("--mydrive",default="/content/drive/MyDrive");a.add_argument("--repo-root",required=True);x=a.parse_args()
 try:return run(x)
 except Exception as e:
  out,p=paths(Path(x.mydrive));out.mkdir(parents=True,exist_ok=True);c.dump_json(p["fatal"],{"record":"STAGE7_EVALUATION_FATAL_v1","status":"FAIL_CLOSED","failed_at_utc":now(),"error_type":type(e).__name__,"error":str(e),"traceback":traceback.format_exc(),"no_rule_change_authorized":True,"ECON_HOLDOUT1000":"SEALED"});print(f"FAIL-CLOSED: {type(e).__name__}: {e}",flush=True);print(traceback.format_exc(),flush=True);return 2
if __name__=="__main__":raise SystemExit(main())
