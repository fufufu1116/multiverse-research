#!/usr/local/python/current/bin/python
from pathlib import Path
from unittest.mock import patch
import hashlib
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_11_STEP3_COMPLETE_TRANSPORT_ACTION_20260830.txt'
RUNNER=ROOT/'g/r'
EXPECTED_ACTION_LEN=561
EXPECTED_ACTION_SHA='12190dece28a387130a28d1033bffeb47b5b03bc6ccbbd76f9907c33b1549793'
EXPECTED_ACTION_BLOB='c812a0e573835b4a1946371f0a68caa9b7c92be2'
EXPECTED_RUNNER_LEN=1414
EXPECTED_RUNNER_SHA='8285553a0b8d7593b0382bb97c5925fd61be4d8980923f49c81d2ddc71648d64'
EXPECTED_RUNNER_BLOB='4f96c8e853357be4b57a864240c365208f755d1d'

def blob_sha(d):
    return hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()

a=ACTION.read_bytes()
r=RUNNER.read_bytes()
assert len(a)==EXPECTED_ACTION_LEN
assert hashlib.sha256(a).hexdigest()==EXPECTED_ACTION_SHA
assert blob_sha(a)==EXPECTED_ACTION_BLOB
assert b'\n' not in a
assert len(r)==EXPECTED_RUNNER_LEN
assert hashlib.sha256(r).hexdigest()==EXPECTED_RUNNER_SHA
assert blob_sha(r)==EXPECTED_RUNNER_BLOB
print('exact_action_and_runner_identity:PASS')

# Full exact action must parse; every strict nonempty prefix must remain syntactically incomplete.
text=a.decode('utf-8')
assert subprocess.run(['/bin/bash','-n','-c',text],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
for i in range(1,len(text)):
    rc=subprocess.run(['/bin/bash','-n','-c',text[:i]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode
    assert rc!=0, ('unexpected_parseable_truncation',i,text[:i])
print('all_strict_prefix_truncations_fail_parse:PASS')

# Execute the exact embedded Python payload unchanged with fault-injected subprocess boundaries.
marker="-Bc'"
suffix="' || exit 92; }"
start=text.index(marker)+len(marker)
end=text.rindex(suffix)
py=text[start:end]

def run_payload(fetch,dispatch):
    with patch('subprocess.check_output',side_effect=fetch), patch('subprocess.run',side_effect=dispatch):
        try:
            exec(compile(py,'<v19.7.11-exact-action-payload>','exec'),{})
        except SystemExit as e:
            return e.code

# One-byte/identity tamper: dispatch must never be reached.
called=[]
def fetch_tamper(*args,**kwargs):
    return b'X'*EXPECTED_RUNNER_LEN
def dispatch_must_not_run(*args,**kwargs):
    called.append((args,kwargs))
    raise AssertionError('dispatch reached after identity failure')
assert run_payload(fetch_tamper,dispatch_must_not_run)==92
assert called==[]
print('tamper_rejected_before_runner_dispatch:PASS')

# Fetch failure: no dispatch and fail closed before runner dispatch.
called=[]
def fetch_fail(*args,**kwargs):
    raise subprocess.CalledProcessError(22,['curl'])
def dispatch_after_fetch_fail(*args,**kwargs):
    called.append((args,kwargs))
    raise AssertionError('dispatch reached after fetch failure')
try:
    run_payload(fetch_fail,dispatch_after_fetch_fail)
except subprocess.CalledProcessError:
    pass
else:
    raise AssertionError('fetch failure did not propagate nonzero')
assert called==[]
print('fetch_failure_before_runner_dispatch:PASS')

# Exact verified bytes must be the exact bytes handed to /bin/bash; dispatch failure must propagate.
seen=[]
class R:
    returncode=37
def fetch_exact(*args,**kwargs):
    return r
def dispatch_fail(args,**kwargs):
    seen.append((args,kwargs))
    assert args==['/bin/bash']
    assert kwargs.get('input') is r
    return R()
assert run_payload(fetch_exact,dispatch_fail)==37
assert len(seen)==1
print('exact_verified_bytes_to_bash_and_dispatch_failure_propagates:PASS')

# Shell-level barrier structure is part of the exact action and the final closing brace is mandatory.
assert text.startswith('{ exec /usr/local/python/current/bin/python ')
assert text.endswith("' || exit 92; }")
print('shell_exec_failure_barrier_and_final_completeness_gate:PASS')
print('PHASE_C_V19_7_11_EXACT_ACTION_FAULT_HARNESS_PASS')
