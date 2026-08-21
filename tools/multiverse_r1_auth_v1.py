"""R1 authorization guard: consume existing decisions; never mint or elevate grants."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, FrozenSet, Optional

P={"P0_READ_PUBLIC_OR_CANONICAL":0,"P1_REVERSIBLE_INTERNAL_WRITE":1,"P2_EXTERNAL_OR_SHARED_WRITE":2,"P3_MATERIAL_OPERATION":3,"P4_OWNER_GATE_REQUIRED":4,"P5_PROHIBITED":5}
AUTH_FIELDS={"authorization_decision_id","policy_generation","policy_digest","actor_role","actor_instance","operation","target","permission_class_requested","permission_ceiling","scope","data_exposure_scope","issued_at","expires_at","grant_ref","owner_gate_ref","revocation_generation_seen","safe_mode_generation_seen","decision","reason_codes","evidence_refs"}

class AuthorizationDenied(RuntimeError): pass

@dataclass(frozen=True)
class AuthorizationRuntime:
    policy_generation:str
    policy_digest:str
    revocation_generation:int
    safe_mode_generation:int
    now:datetime
    actor_role:str
    actor_instance:str
    valid_grant_refs:FrozenSet[str]
    expected_owner_gate_ref:Optional[str]=None
    safe_mode_active:bool=False

def _deny(code:str)->None: raise AuthorizationDenied(code)
def _time(value:Any)->datetime:
    try: out=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc: raise AuthorizationDenied("AUTH_TIME_MALFORMED") from exc
    if out.tzinfo is None: _deny("AUTH_TIME_MUST_BE_OFFSET_AWARE")
    return out.astimezone(timezone.utc)

def validate_authorization(decision:dict,runtime:AuthorizationRuntime,*,operation:str,target:str,permission_class:str,data_exposure_scope:str)->None:
    if not isinstance(decision,dict): _deny("AUTH_DECISION_NOT_OBJECT")
    if AUTH_FIELDS-set(decision): _deny("AUTH_REQUIRED_FIELDS_MISSING")
    if decision["decision"]!="ALLOW": _deny("AUTH_DECISION_NOT_ALLOW")
    requested,ceiling=decision["permission_class_requested"],decision["permission_ceiling"]
    if requested not in P or ceiling not in P or permission_class not in P: _deny("AUTH_PERMISSION_CLASS_UNKNOWN")
    if requested=="P5_PROHIBITED" or permission_class=="P5_PROHIBITED": _deny("AUTH_P5_PROHIBITED")
    if requested!=permission_class: _deny("AUTH_PERMISSION_CLASS_REQUEST_MISMATCH")
    if (decision["actor_role"],decision["actor_instance"])!=(runtime.actor_role,runtime.actor_instance): _deny("AUTH_ACTOR_MISMATCH")
    if decision["policy_generation"]!=runtime.policy_generation or decision["policy_digest"]!=runtime.policy_digest: _deny("AUTH_POLICY_STALE")
    if decision["revocation_generation_seen"]!=runtime.revocation_generation: _deny("AUTH_REVOCATION_STALE")
    if decision["safe_mode_generation_seen"]!=runtime.safe_mode_generation: _deny("AUTH_SAFE_MODE_GENERATION_STALE")
    if runtime.safe_mode_active and permission_class!="P0_READ_PUBLIC_OR_CANONICAL": _deny("AUTH_SAFE_MODE_DENY")
    now=runtime.now.astimezone(timezone.utc)
    if _time(decision["issued_at"])>now or _time(decision["expires_at"])<=now: _deny("AUTH_TIME_INVALID")
    if decision["operation"]!=operation or decision["target"]!=target: _deny("AUTH_OPERATION_TARGET_MISMATCH")
    if decision["data_exposure_scope"]!=data_exposure_scope: _deny("AUTH_DATA_EXPOSURE_MISMATCH")
    scope=decision["scope"]
    if not isinstance(scope,dict) or scope.get("operation")!=operation or scope.get("target")!=target or scope.get("data_exposure_scope",data_exposure_scope)!=data_exposure_scope: _deny("AUTH_SCOPE_MISMATCH")
    if P[permission_class]>P[ceiling]: _deny("AUTH_PERMISSION_CEILING_EXCEEDED")
    if not isinstance(decision["authorization_decision_id"],str) or not decision["authorization_decision_id"]: _deny("AUTH_DECISION_ID_INVALID")
    if not isinstance(decision["reason_codes"],list) or not all(isinstance(x,str) for x in decision["reason_codes"]): _deny("AUTH_REASON_CODES_INVALID")
    if not isinstance(decision["evidence_refs"],list) or not all(isinstance(x,str) for x in decision["evidence_refs"]): _deny("AUTH_EVIDENCE_REFS_INVALID")
    if permission_class!="P0_READ_PUBLIC_OR_CANONICAL":
        grant=decision["grant_ref"]
        if not isinstance(grant,str) or not grant: _deny("AUTH_GRANT_REQUIRED")
        if grant not in runtime.valid_grant_refs: _deny("AUTH_GRANT_INVALID_OR_REVOKED")
    if permission_class=="P4_OWNER_GATE_REQUIRED":
        if not runtime.expected_owner_gate_ref or decision["owner_gate_ref"]!=runtime.expected_owner_gate_ref: _deny("AUTH_OWNER_GATE_MISSING_OR_MISMATCHED")
