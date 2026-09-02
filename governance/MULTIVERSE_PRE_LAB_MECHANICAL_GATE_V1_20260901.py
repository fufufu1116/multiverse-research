#!/usr/bin/env python3
"""Review-only pre-Lab mechanical gate. Mechanical PASS never grants security authority."""
from __future__ import annotations
import ast,hashlib,json,os,pathlib,py_compile,re,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];RC=92
EXPECTED={
'.devcontainer/Dockerfile':'dockerfile',
'.devcontainer/devcontainer.json':'json',
'.devcontainer/v19_7_36_requirements.txt':'text',
'.github/workflows/multiverse-v36-prelab-exact-image-build.yml':'text',
'MULTIVERSE_PRELIVE_START_HERE.md':'text',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go':'go-compose',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_ATTACH_READY_STATUS_ADDON_20260901.go':'go-addon',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_MANUAL_ARM_LAUNCHER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_ROOT_ANCHOR_PRODUCER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_CONTROL_PLANE_RUNNER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RUNTIME_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_RECURSIVE_CLOSURE_MANIFEST_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_PYTHON_ACTUAL_USE_SELFTEST_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json':'json',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json':'json',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_20260901.py':'python'}

def fail(c,m):print(f'PRE_LAB_MECHANICAL_GATE_DENIED:{c}:{m}',file=sys.stderr);raise SystemExit(RC)
def data(r):return (ROOT/r).read_bytes()
def text(r):return data(r).decode()
def gitblob(b):
 h=hashlib.sha1();h.update(f'blob {len(b)}\0'.encode());h.update(b);return h.hexdigest()
def run(cmd,env=None,ok=(0,)):
 p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 sys.stdout.write(p.stdout);sys.stderr.write(p.stderr)
 if p.returncode not in ok:fail('BUILD_OR_SYNTAX',f'{cmd[0]}:rc={p.returncode}')
 return p
def require(s,needles,code):
 for n in needles:
  if n not in s:fail(code,n)
def check_kind(r,w):
 if not (ROOT/r).is_file():fail('EXPECTED_FILE_MISSING',r)
 b=data(r);s=b.lstrip()
 try:
  if w=='json':json.loads(b)
  elif w=='python':ast.parse(b.decode(),filename=r)
  elif w.startswith('go') and not s.startswith(b'package main'):fail('GO_CONTENT_TYPE',r)
  elif w=='dockerfile' and not re.search(br'(?m)^FROM\s+',b):fail('DOCKERFILE_CONTENT_TYPE',r)
 except Exception as e:fail('PARSE',f'{r}:{type(e).__name__}')

def main():
 for r,w in EXPECTED.items():check_kind(r,w)
 d=text('.devcontainer/Dockerfile');q=json.loads(data('.devcontainer/devcontainer.json'))
 if q.get('build',{}).get('dockerfile')!='Dockerfile' or q.get('build',{}).get('context')!='..':fail('DEVCONTAINER_BUILD_MAPPING','unexpected')
 if q.get('containerUser')!='root' or q.get('remoteUser')!='codespace' or q.get('overrideCommand') is not True:fail('DEVCONTAINER_USER_BOUNDARY','unexpected')
 if q.get('postAttachCommand')!=['/usr/local/bin/multiverse-v36-ui-ready-v7r7']:fail('POST_ATTACH_COMMAND','must-be-writer-only')
 if q.get('runArgs')!=['--cap-drop=ALL','--cap-add=CHOWN','--cap-add=SETUID','--cap-add=SETGID']:fail('DEVCONTAINER_CAPS','unexpected')
 if q.get('customizations',{}).get('codespaces',{}).get('openFiles')!=['MULTIVERSE_PRELIVE_START_HERE.md']:fail('DEVCONTAINER_OPEN_FILE','unexpected')
 for n,l in enumerate(d.splitlines(),1):
  m=re.match(r'^\s*(COPY|ADD)\s+(?:--\S+\s+)*([^\s]+)',l)
  if m and not m.group(2).startswith(('http://','https://','--from=')) and not (ROOT/m.group(2)).is_file():fail('DOCKER_COPY_SOURCE_MISSING',f'{n}:{m.group(2)}')
 if re.search(r'(?m)^\s*ENTRYPOINT\b',d):fail('SESSION_GATE_AUTOSTART','Dockerfile ENTRYPOINT must be absent')
 if 'multiverse-v36-session-gate-v7r6' in d:fail('STALE_V7R6_BINARY_WIRING','present')
 require(d,[
  'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_ATTACH_READY_STATUS_ADDON_20260901.go',
  'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_MANUAL_ARM_LAUNCHER_20260901.go',
  'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go',
  '-o /usr/local/sbin/multiverse-v36-session-gate-v7r7 /tmp/session-gate.go /tmp/session-status-addon-v7r7.go',
  '-o /usr/local/bin/multiverse-v36-arm-v7r7 /tmp/manual-arm-v7r7.go',
  '-o /usr/local/bin/multiverse-v36-ui-ready-v7r7 /tmp/ui-ready-v7r7.go',
  '/usr/local/sbin/multiverse-v36-session-gate-v7r7 build-selftest',
  'chmod 4555 /usr/local/bin/multiverse-v36-arm-v7r7',
  "test \"$(stat -c '%u %g %a' /usr/local/bin/multiverse-v36-arm-v7r7)\" = '0 0 4555'",
  '! -path /usr/local/bin/multiverse-v36-arm-v7r7',
  '/tmp/image-identity-builder.py'], 'DOCKER_V7R7_WIRING')
 gate=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go')
 require(gate,['apiHardBudget = 40','apiReserveRemaining = 8','pollInterval = 30 * time.Second','approvalWindow = 10 * time.Minute','q.Set("since"','cursorOverlap = 2 * time.Second','approvalDeadline := issued.Add(approvalWindow)','c.CreatedAt.After(approvalDeadline)','PAGINATION_RACE_SELFTEST_PASS','RATE_HEADERS_FAIL_CLOSED_SELFTEST_PASS','STRICT_APPROVAL_WINDOW_SELFTEST_PASS','APPROVE V19.7.36 v7r6 ONE-SHOT LIVE'], 'INHERITED_GATE_REGRESSION')
 if 'watermark = d' in gate or 'if d.After(watermark)' in gate:fail('PAGINATION_WATERMARK_REGRESSION','final-page-watermark-present')
 writer=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go')
 require(writer,['PHASE_C_V19_7_36_V7R7_UI_READY','image_identity_sha256=','timer_state=NOT_STARTED','RETURN_TO_CORE_BEFORE_ARM','O_EXCL','O_NOFOLLOW','existingReadyExact','imageIdentitySHA256','PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_PASS'], 'UI_READY_WRITER_WIRING')
 for forbidden in ['SESSION_CHALLENGE','githubServerNow','syscall.Exec(','multiverse-v36-session-gate-v7r7 build-selftest']:
  if forbidden in writer:fail('POST_ATTACH_MUST_NOT_ARM',forbidden)
 arm=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_MANUAL_ARM_LAUNCHER_20260901.go')
 require(arm,['/usr/local/sbin/multiverse-v36-session-gate-v7r7','/run/multiverse-v36-v7r7-arm.lock','syscall.O_EXCL','SETUID_BOUNDARY','Setresuid(0, 0, 0)','NoNewPrivs:\\t1','CapEff','CapBnd','os.Clearenv()','imageIdentitySHA256','image_identity_sha256=','READY_BINDING','CONTROL_BINDING','SESSION_STATUS_PREEXISTS','syscall.Exec("/proc/self/fd/3"','timer_starts_inside_session_gate_after_trusted_server_time'], 'MANUAL_ARM_WIRING')
 for forbidden in ['exec.Command(','/bin/sh','/bin/bash','approvalPrefix']:
  if forbidden in arm:fail('MANUAL_ARM_SURFACE',forbidden)
 addon=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_ATTACH_READY_STATUS_ADDON_20260901.go')
 require(addon,['/run/multiverse-v36-v7r7','ui_mirror=NONAUTHORITATIVE_STATIC','syscall.Openat','syscall.Renameat','PHASE_C_V19_7_36_V7R7_ARMED','STARTING_TRUSTED_GITHUB_SERVER_TIME','PHASE_C_V19_7_36_V7R6_SESSION_CHALLENGE ','PHASE_C_V19_7_36_V7R6_WAITING_FOR_EXTERNAL_SESSION_BINDING','O_EXCL','O_NOFOLLOW','STDOUT_RESTORE','DEVICE_CODE_SHOULD_REMAIN_TERMINAL_ONLY_AFTER_RESTORE','PHASE_C_V19_7_36_V7R7_ATTACH_READY_OBSERVABILITY_SELFTEST_PASS','PHASE_C_V19_7_36_V7R7_UI_RETAINED_FD_ATOMIC_REPLACE_PASS','PHASE_C_V19_7_36_V7R7_UI_DIRECTORY_FD_BINDING_PASS'], 'ATTACH_READY_STATUS_WIRING')
 if '/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r7-session-status.txt' in addon:fail('ATTACH_READY_STATUS_WIRING','legacy-persistedshare-authority-present')
 builder=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py')
 require(builder,['V19.7.36-v7r7-image-identity','/usr/local/sbin/multiverse-v36-session-gate-v7r7','/usr/local/bin/multiverse-v36-arm-v7r7','/usr/local/bin/multiverse-v36-ui-ready-v7r7'], 'IMAGE_IDENTITY_V7R7_WIRING')
 start=text('MULTIVERSE_PRELIVE_START_HERE.md')
 require(start,['WAITING_FOR_CODESPACE_ATTACH_READY','Do not start PRE-LIVE from this placeholder','timer_state=NOT_STARTED','Runtime: OFF'], 'START_HERE_PLACEHOLDER')
 hist=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py')
 require(hist,['range(1,601)','LATE_SECONDS=510','full_used==28','updated_at > since'], 'RATE_BUDGET_HISTORY_SELFTEST_WIRING')
 run([sys.executable,'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py'])
 waittest=text('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_20260901.py')
 require(waittest,['const pollInterval = 30 * time.Second','const pollInterval = 200 * time.Millisecond','waitReceipt(cl, b, name, challenge, identity, issued, deadline)','deltaStarted.Before(deadline)','deltaFinished.Before(deadline)','tr.calls != 1','elapsed >= 150*time.Millisecond','PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_PASS'], 'WAIT_PATH_SELFTEST_WIRING')
 run([sys.executable,'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_20260901.py'])
 bnd=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json'))['step3'];pb=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py')
 if bnd['git_blob']!=gitblob(pb) or bnd['sha256']!=hashlib.sha256(pb).hexdigest() or bnd['size']!=len(pb) or bnd.get('mode')!='NONMUTATING' or bnd.get('mutations')!=0:fail('STEP3_BINDING','mismatch')
 a=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json'))
 if a.get('version')!='V19.7.36-v7r7' or a.get('authority')!='REVIEW_ONLY_NO_LIVE_AUTHORITY' or a.get('runtime')!='OFF':fail('ASSEMBLY_MANIFEST','authority')
 rem=a.get('attach_ready_manual_arm_remediation',{})
 if rem.get('container_creation_starts_challenge') is not False or rem.get('post_attach_starts_challenge') is not False or rem.get('manual_arm_starts_gate') is not True or rem.get('pre_arm_timer_state')!='NOT_STARTED' or rem.get('pre_arm_image_identity_binding') is not True:fail('ASSEMBLY_ATTACH_READY','semantics')
 inherited=a.get('inherited_v7r6_security',{})
 if inherited.get('external_session_gate_source_unchanged') is not True or inherited.get('approval_window_seconds')!=600 or inherited.get('api_hard_budget_requests')!=40 or inherited.get('step3_mode')!='NONMUTATING' or inherited.get('production_mutation') is not False or inherited.get('runtime_activation') is not False:fail('ASSEMBLY_INHERITED_SECURITY','mismatch')
 neg=set(a.get('negative_mechanical_requirements',[]))
 for required in ['no_session_gate_entrypoint','post_attach_writer_only_no_arm','pre_arm_timer_not_started','pre_arm_image_identity_exactly_bound','duplicate_arm_lock_rejected','only_manual_arm_launcher_retains_setuid_or_setgid_in_hardened_search_boundary','manual_arm_setuid_transition_proven_in_exact_image','exact_final_tree_docker_build_passes']:
  if required not in neg:fail('ASSEMBLY_NEGATIVE',required)
 with tempfile.TemporaryDirectory(prefix='multiverse-prelab-') as td:
  for r,w in EXPECTED.items():
   p=ROOT/r
   if w=='python':py_compile.compile(str(p),cfile=str(pathlib.Path(td)/(p.name+'.pyc')),doraise=True)
   elif w=='go':
    if not shutil.which('go'):fail('GO_TOOL_UNAVAILABLE',r)
    e=dict(os.environ);e['CGO_ENABLED']='0';run(['go','build','-trimpath','-buildvcs=false','-o',str(pathlib.Path(td)/p.stem),str(p)],e)
  e=dict(os.environ);e['CGO_ENABLED']='0'
  gate_alone=str(pathlib.Path(td)/'session-gate-v7r6-alone')
  composed=str(pathlib.Path(td)/'session-gate-v7r7-composed')
  run(['go','build','-trimpath','-buildvcs=false','-o',gate_alone,'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go'],e)
  run([gate_alone,'build-selftest'],e)
  run(['go','build','-trimpath','-buildvcs=false','-o',composed,'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_ATTACH_READY_STATUS_ADDON_20260901.go'],e)
  run([composed,'build-selftest'],e)
 wf=text('.github/workflows/multiverse-v36-prelab-exact-image-build.yml')
 if 'workflow_dispatch' in wf:fail('WORKFLOW_DISPATCH_PROHIBITED','present')
 if not shutil.which('docker'):fail('DOCKER_TOOL_UNAVAILABLE','mandatory-final-tree-build-not-run')
 tag=os.environ.get('MULTIVERSE_PRELAB_DOCKER_TAG','').strip() or f'multiverse-v7r7-prelab:local-{os.getpid()}'
 run(['docker','build','--progress=plain','--no-cache','-t',tag,'-f','.devcontainer/Dockerfile','.'])
 p=run(['docker','image','inspect','--format','{{json .Config.Entrypoint}}',tag])
 if 'multiverse-v36-session-gate' in p.stdout:fail('SESSION_GATE_IMAGE_ENTRYPOINT','present')
 p=run(['docker','run','--rm','--entrypoint','/bin/cat',tag,'/opt/multiverse/v36/image-identity-v7r3.json'])
 try:identity=json.loads(p.stdout)
 except Exception:fail('IMAGE_IDENTITY_RUNTIME','invalid-json')
 if identity.get('version')!='V19.7.36-v7r7-image-identity':fail('IMAGE_IDENTITY_RUNTIME','version')
 paths=[x.get('path') for x in identity.get('objects',[])]
 for required in ['/usr/local/sbin/multiverse-v36-session-gate-v7r7','/usr/local/bin/multiverse-v36-arm-v7r7','/usr/local/bin/multiverse-v36-ui-ready-v7r7']:
  if required not in paths:fail('IMAGE_IDENTITY_RUNTIME',required)
 identity_sha256=hashlib.sha256(p.stdout.encode()).hexdigest()
 p=run(['docker','run','--rm','--entrypoint','/usr/bin/stat',tag,'-c','%u %g %a','/usr/local/bin/multiverse-v36-arm-v7r7'])
 if p.stdout.strip()!='0 0 4555':fail('ARM_SETUID_MODE',p.stdout.strip())
 p=run(['docker','run','--rm','--user','codespace','--cap-drop=ALL','--cap-add=CHOWN','--cap-add=SETUID','--cap-add=SETGID','-e','CODESPACES=false','-e','CODESPACE_NAME=mechanical-test','--entrypoint','/usr/local/bin/multiverse-v36-arm-v7r7',tag],ok=(92,))
 if 'PHASE_C_V19_7_36_V7R7_ARM_LAUNCHER_DENIED:CODESPACES' not in p.stderr or 'SETUID_BOUNDARY' in p.stderr or 'CAPS' in p.stderr:fail('ARM_SETUID_BEHAVIOR','did-not-cross-reviewed-boundary')
 print('V7R7_MANUAL_ARM_SETUID_BEHAVIOR_PASS')
 print('PRELAB_IMAGE_IDENTITY_SHA256='+identity_sha256)
 print('REAL_DOCKER_IMAGE_BUILD_PASS');print('PRE_LAB_MECHANICAL_GATE_PASS');print('SECURITY_AUTHORITY_GRANTED=false');print('RUNTIME=OFF')
if __name__=='__main__':main()