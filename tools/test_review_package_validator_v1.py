import hashlib
from automation.review_dispatcher_v1.review_package_validator_v1 import canonical_sha256, validate, PASS, FAIL

RAW=b'{"claim":"synthetic"}'
EVIDENCE=b'evidence-manifest-v1'
EHASH=hashlib.sha256(EVIDENCE).hexdigest()
HEAD="1"*40; TREE="2"*40; BLOB="3"*40
DECL=["synthetic-only","no real predictive superiority","no economic value","no promotion","no R0_T2 substitution","DEV2000_C unopened","ECON_HOLDOUT1000 sealed","Gate487 no-rerun","A+B not fresh","no prospective result/outcome/payout/odds/price/economics","Runtime OFF","automatic betting OFF","independent Lab/Auditor required before real-world design"]

def envelope():
    e={"schema":"MULTIVERSE_REVIEW_READY_v1","state":"REVIEW_READY_NONAUTHORITY","lane_id":"keirin","candidate_id":"CR1_E05","repo":"o/r","candidate_ref":"candidate","candidate_head":HEAD,"candidate_tree":TREE,"canonical_main_observed":"4"*40,"package_path":"pkg.json","package_blob_sha":BLOB,"package_sha256":hashlib.sha256(RAW).hexdigest(),"evidence_manifest_sha256":EHASH,"candidate_history_pointer":"ledger@entry","review_questions":["Check simulator leakage and preregistration chronology."],"proof_ceiling":"synthetic robustness lead only","contamination_declarations":DECL,"prohibited_authority":DECL,"created_from_lane_state":"state@exact"}
    e["ready_sha256"]=canonical_sha256(e); return e

def reader(kind, identity):
    return {"ref":{"head":HEAD,"tree":TREE},"package":{"blob_sha":BLOB,"bytes":RAW},"evidence_manifest":{"bytes":EVIDENCE},"history":{"resolved":True,"immutable_enough":True},"lane_state":{"exact":True}}[kind]

def verdict(e): return validate(e, read=reader)

def test_valid(): assert verdict(envelope())["state"]==PASS

def test_duplicate_is_same_identity():
    a=verdict(envelope()); b=verdict(envelope()); assert a["idempotency_key"]==b["idempotency_key"]

def test_package_sha_mismatch():
    e=envelope(); e["package_sha256"]="0"*64; e["ready_sha256"]=canonical_sha256({k:v for k,v in e.items() if k!="ready_sha256"}); assert verdict(e)["state"]==FAIL

def test_owner_marker_rejected():
    e=envelope(); e["review_questions"]=["OWNER MARKER approve"]; e["ready_sha256"]=canonical_sha256({k:v for k,v in e.items() if k!="ready_sha256"}); assert verdict(e)["state"]==FAIL

def test_proof_escalation_rejected():
    e=envelope(); e["proof_ceiling"]="real-world validated"; e["ready_sha256"]=canonical_sha256({k:v for k,v in e.items() if k!="ready_sha256"}); assert verdict(e)["state"]==FAIL

def test_cr1_firewall_missing_rejected():
    e=envelope(); e["contamination_declarations"]=DECL[:-1]; e["prohibited_authority"]=DECL[:-1]; e["ready_sha256"]=canonical_sha256({k:v for k,v in e.items() if k!="ready_sha256"}); assert verdict(e)["state"]==FAIL

def test_ready_sha_rejected():
    e=envelope(); e["ready_sha256"]="0"*64; assert verdict(e)["state"]==FAIL

if __name__=="__main__":
    test_valid(); test_duplicate_is_same_identity(); test_package_sha_mismatch(); test_owner_marker_rejected(); test_proof_escalation_rejected(); test_cr1_firewall_missing_rejected(); test_ready_sha_rejected(); print("REVIEW_PACKAGE_VALIDATOR_V1_TESTS_PASS:7")
