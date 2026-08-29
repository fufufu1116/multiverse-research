#!/usr/local/python/current/bin/python
from pathlib import Path
from unittest.mock import patch
import hashlib
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_12_STEP3_COMPLETE_TRANSPORT_ACTION_20260830.txt'
RUNNER=ROOT/'g/r'
EXPECTED_ACTION_LEN=570
EXPECTED_ACTION_SHA='d0b677cf5babb538da439646487f8b74b044b0c8db43b7441ce13505464cc689'
EXPECTED_ACTION_BLOB='eb224cd040946f6b1421ebc7d8e5d95ecbfa30e5'
EXPECTED_RUNNER_LEN=1414
EXPECTED_RUNNER_SHA='8285553a0b8d7593b0382bb97c5925fd61be4d8980923f49c81d2ddc71648d64'
EXPECTED_RUNNER_BLOB='4f96c8e853357be4b57a864240c365208f755d1d'
EXPECTED_FETCH_EXE='/usr/bin/curl'

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

text=a.decode('utf-8')
assert subprocess.run(['/bin/bash','-n','-c',text],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
for i in range(1,len(text)):
    rc=subprocess.run(['/bin/bash','-n','-c',text[:i]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode
    assert rc!=0, ('unexpected_parseable_truncation',i,text[:i])
print('all_strict_prefix_truncations_fail_parse:PASS')

marker="-Bc'"
suffix="' || exit 92; }"
start=text.index(marker)+len(marker)
end=text.rindex(suffix)
py=text[start:end]

def run_payload(fetch,dispatch):
    with patch('subprocess.check_output',side_effect=fetch), patch('subprocess.run',side_effect=dispatch):
        try:
            exec(compile(py,'<v19.7.12-exact-action-payload>','exec'),{})
        except SystemExit as e:
            return e.code

# Fetch executable identity is part of the exact action and is absolute.
fetch_argv=[]
def fetch_exact(*args,**kwargs):
    fetch_argv.append(args[0])
    return r
class R0:
    returncode=0
def dispatch_ok(args,**kwargs):
    assert args==['/bin/bash']
    assert kwargs.get('input') is r
    return R0()
assert run_payload(fetch_exact,dispatch_ok)==0
assert fetch_argv and fetch_argv[0][0]==EXPECTED_FETCH_EXE
assert 'curl' not in fetch_argv[0][:1]
print('absolute_fetch_executable_binding:PASS')

# One-byte/identity tamper must be rejected before dispatch.
called=[]
def fetch_tamper(*args,**kwargs):
    assert args[0][0]==EXPECTED_FETCH_EXE
    return b'X'*EXPECTED_RUNNER_LEN
def dispatch_must_not_run(*args,**kwargs):
    called.append((args,kwargs))
    raise AssertionError('dispatch reached after identity failure')
assert run_payload(fetch_tamper,dispatch_must_not_run)==92
assert called==[]
print('tamper_rejected_before_runner_dispatch:PASS')

# Fetch failure must occur on the pinned executable and before runner dispatch.
called=[]
def fetch_fail(*args,**kwargs):
    assert args[0][0]==EXPECTED_FETCH_EXE
    raise subprocess.CalledProcessError(22,args[0])
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
print('pinned_fetch_failure_before_runner_dispatch:PASS')

# Exact verified bytes must be the exact bytes handed to Bash; dispatch failure propagates.
seen=[]
class R37:
    returncode=37
def dispatch_fail(args,**kwargs):
    seen.append((args,kwargs))
    assert args==['/bin/bash']
    assert kwargs.get('input') is r
    return R37()
assert run_payload(fetch_exact,dispatch_fail)==37
assert len(seen)==1
print('exact_verified_bytes_to_bash_and_dispatch_failure_propagates:PASS')

assert text.startswith('{ exec /usr/local/python/current/bin/python ')
assert text.endswith("' || exit 92; }")
assert '["/usr/bin/curl"' in text
print('shell_exec_failure_barrier_final_gate_and_absolute_curl:PASS')
print('PHASE_C_V19_7_12_EXACT_ACTION_FAULT_HARNESS_PASS')
