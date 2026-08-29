set +e
set +x
umask 077
phase_c_verify
PHASE_C_V19_7_3_VERIFY_RC=$?
if [ "$PHASE_C_V19_7_3_VERIFY_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_V19_7_3_STEP3_VERIFY_STOP_DELETE_CODESPACE_RC=$PHASE_C_V19_7_3_VERIFY_RC" >&2; unset PHASE_C_V19_7_3_VERIFY_RC; return 92; fi
unset PHASE_C_V19_7_3_VERIFY_RC
PHASE_C_V19_7_3_PREFLIGHT_OUT="$(cd "$EXEC_ROOT" && /usr/local/python/current/bin/python -B tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py)"
PHASE_C_V19_7_3_PREFLIGHT_RC=$?
if [ "$PHASE_C_V19_7_3_PREFLIGHT_RC" -ne 0 ]; then command printf '%s\n' 'PHASE_C_V19_7_3_NONMUTATING_PREFLIGHT_STOP_DELETE_CODESPACE' >&2; unset PHASE_C_V19_7_3_PREFLIGHT_OUT PHASE_C_V19_7_3_PREFLIGHT_RC; return 92; fi
/usr/local/python/current/bin/python -B -c 'import json,sys; d=json.loads(sys.argv[1]); assert d.get("status")=="PHASE_C_NONMUTATING_PREFLIGHT_PASS"; assert d.get("production_mutation_performed") is False; assert d.get("runtime_activation_performed") is False' "$PHASE_C_V19_7_3_PREFLIGHT_OUT" || { command printf '%s\n' 'PHASE_C_V19_7_3_PREFLIGHT_RESULT_INVALID_STOP_DELETE_CODESPACE' >&2; unset PHASE_C_V19_7_3_PREFLIGHT_OUT PHASE_C_V19_7_3_PREFLIGHT_RC; return 92; }
unset PHASE_C_V19_7_3_PREFLIGHT_OUT PHASE_C_V19_7_3_PREFLIGHT_RC
command printf '%s\n' 'PHASE_C_V19_7_3_NONMUTATING_STEP3_PASS'