set +e
set +x
set -u
umask 077
TRUSTED_PY='/usr/local/python/current/bin/python'
RECOVERY_ROOT="${RECOVERY_ROOT:-}"
V2_PATH="$RECOVERY_ROOT/governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRODUCTION_EXECUTION_OWNER_GATE_CANDIDATE_20260824_v1.json"
STEP1_PATH='/dev/shm/multiverse-r1-stage1-phase-c-recovery-step1.sh'
V2_BLOB='67f158cf1d79846879d4f2238625863336372e24'
STEP1_SHA256='bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74'
STEP1_BYTES='4687'
test -x "$TRUSTED_PY" || { command printf '%s\n' 'PHASE_C_RECOVERY_TRUSTED_PYTHON_BINARY_MISSING_STOP_DELETE_CODESPACE' >&2; exit 89; }
test "$(command -v python)" = "$TRUSTED_PY" || { command printf '%s\n' 'PHASE_C_RECOVERY_TRUSTED_PYTHON_RESOLUTION_MISMATCH_STOP_DELETE_CODESPACE' >&2; exit 89; }
command printf '%s\n' 'PHASE_C_RECOVERY_TRUSTED_PYTHON_BINDING_PASS'
test -n "$RECOVERY_ROOT" && test -d "$RECOVERY_ROOT" && test ! -L "$RECOVERY_ROOT" || { command printf '%s\n' 'PHASE_C_RECOVERY_CONTROL_ROOT_INVALID_STOP_DELETE_CODESPACE' >&2; exit 88; }
test -f "$V2_PATH" && test ! -L "$V2_PATH" && test ! -x "$V2_PATH" || { command printf '%s\n' 'PHASE_C_RECOVERY_V2_GATE_FILE_INVALID_STOP_DELETE_CODESPACE' >&2; exit 88; }
test "$(command env -i PATH="/usr/local/bin:/usr/bin:/bin" HOME="/dev/shm/multiverse-r1-stage1-phase-c-recovery-control-home" LANG="C" LC_ALL="C" GIT_CONFIG_NOSYSTEM="1" GIT_CONFIG_SYSTEM="/dev/null" GIT_CONFIG_GLOBAL="/dev/null" GIT_ATTR_NOSYSTEM="1" GIT_NO_REPLACE_OBJECTS="1" GIT_TERMINAL_PROMPT="0" git -C "$RECOVERY_ROOT" hash-object --no-filters -- "$V2_PATH")" = "$V2_BLOB" || { command printf '%s\n' 'PHASE_C_RECOVERY_V2_GATE_BLOB_MISMATCH_STOP_DELETE_CODESPACE' >&2; exit 88; }
test ! -e "$STEP1_PATH" && test ! -L "$STEP1_PATH" || { command printf '%s\n' 'PHASE_C_RECOVERY_STEP1_PATH_PREEXISTS_STOP_DELETE_CODESPACE' >&2; exit 88; }
"$TRUSTED_PY" -B - "$V2_PATH" "$STEP1_PATH" "$STEP1_SHA256" "$STEP1_BYTES" <<'PY'
import hashlib,json,os,stat,sys
gate_path,out,want_sha256,want_len=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
with open(gate_path,"rb",buffering=0) as f:
    gate_bytes=f.read()
gate=json.loads(gate_bytes.decode("utf-8"))
assert gate["schema_version"]=="MULTIVERSE_R1_STAGE1_PHASE_C_PRODUCTION_EXECUTION_OWNER_GATE_CANDIDATE_v2"
src=gate["literal_sequence"]["step1_define_external_verifier_bootstrap_and_preauth"]
marker="phase_c_bootstrap\nPHASE_C_BOOTSTRAP_RC=$?"
assert src.count(marker)==1
i=src.index(marker)
tail=r'''phase_c_bootstrap
PHASE_C_BOOTSTRAP_RC=$?
if [ "$PHASE_C_BOOTSTRAP_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_EXTERNAL_BOOTSTRAP_FAILED_RC=$PHASE_C_BOOTSTRAP_RC" >&2; exit 90; fi
command printf '%s\n' 'PHASE_C_EXTERNAL_BOOTSTRAP_PASS'
phase_c_verify
PHASE_C_PREAUTH_VERIFY_RC=$?
if [ "$PHASE_C_PREAUTH_VERIFY_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_EXTERNAL_VERIFY_BEFORE_PREAUTH_FAILED_RC=$PHASE_C_PREAUTH_VERIFY_RC" >&2; exit 91; fi
command printf '%s\n' 'PHASE_C_EXTERNAL_VERIFY_BEFORE_PREAUTH_PASS'
( cd "$EXEC_ROOT" && exec python -B tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py --preauth )
PHASE_C_PREAUTH_RC=$?
if [ "$PHASE_C_PREAUTH_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_PREAUTH_COMMAND_FAILED_RC=$PHASE_C_PREAUTH_RC" >&2; exit 92; fi
unset PHASE_C_BOOTSTRAP_RC PHASE_C_PREAUTH_VERIFY_RC PHASE_C_PREAUTH_RC
command printf '%s\n' 'PHASE_C_EXTERNAL_BOOTSTRAP_AND_PREAUTH_PASS'
'''
step1=(src[:i]+tail).encode("utf-8")
assert len(step1)==want_len
assert hashlib.sha256(step1).hexdigest()==want_sha256
flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
fd=os.open(out,flags,0o400)
try:
    n=os.write(fd,step1)
    assert n==len(step1)
    os.fsync(fd)
finally:
    os.close(fd)
st=os.lstat(out)
assert stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o400 and st.st_nlink==1 and st.st_uid==os.getuid()
with open(out,"rb",buffering=0) as f:
    rb=f.read()
assert len(rb)==want_len and hashlib.sha256(rb).hexdigest()==want_sha256
PY
PHASE_C_RECOVERY_FETCH_RC=$?
if [ "$PHASE_C_RECOVERY_FETCH_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_RECOVERY_STEP1_RECONSTRUCTION_FAILED_RC=$PHASE_C_RECOVERY_FETCH_RC" >&2; exit 88; fi
/bin/bash -n "$STEP1_PATH" || { rc=$?; command printf '%s\n' "PHASE_C_RECOVERY_STEP1_BASH_N_FAILED_RC=$rc" >&2; exit 88; }
command printf '%s\n' 'PHASE_C_RECOVERY_STEP1_RECONSTRUCTION_VERIFY_PASS'
( . "$STEP1_PATH" )
PHASE_C_RECOVERY_STEP1_RC=$?
command rm -f -- "$STEP1_PATH" || { command printf '%s\n' 'PHASE_C_RECOVERY_STEP1_CLEANUP_FAILED_STOP_DELETE_CODESPACE' >&2; exit 88; }
if [ "$PHASE_C_RECOVERY_STEP1_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_RECOVERY_STEP1_FAILED_RC=$PHASE_C_RECOVERY_STEP1_RC" >&2; exit "$PHASE_C_RECOVERY_STEP1_RC"; fi
unset PHASE_C_RECOVERY_STEP1_RC PHASE_C_RECOVERY_FETCH_RC
command printf '%s\n' 'PHASE_C_RECOVERY_STEP1_PASS_OAUTH_STARTING_NOW'
GH_BROWSER='/bin/true' gh auth login --hostname github.com --git-protocol https --web --scopes 'repo,read:org,gist'
PHASE_C_RECOVERY_OAUTH_RC=$?
if [ "$PHASE_C_RECOVERY_OAUTH_RC" -ne 0 ]; then command printf '%s\n' "PHASE_C_RECOVERY_OAUTH_COMMAND_FAILED_RC=$PHASE_C_RECOVERY_OAUTH_RC" >&2; exit "$PHASE_C_RECOVERY_OAUTH_RC"; fi
unset PHASE_C_RECOVERY_OAUTH_RC
command printf '%s\n' 'PHASE_C_RECOVERY_OAUTH_COMMAND_RETURNED_ZERO_POST_OAUTH_REENTRY_REQUIRED'
