#!/usr/bin/env python3
"""Review-only pre-Lab mechanical gate. Mechanical PASS never grants security authority."""
from __future__ import annotations
import ast,hashlib,json,os,pathlib,py_compile,re,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];RC=92
EXPECTED={
'.devcontainer/Dockerfile':'dockerfile','.devcontainer/devcontainer.json':'json','.devcontainer/v19_7_36_requirements.txt':'text','.github/workflows/multiverse-v36-prelab-exact-image-build.yml':'text',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go':'go','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py':'python','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_ROOT_ANCHOR_PRODUCER_20260901.go':'go','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_CONTROL_PLANE_RUNNER_20260901.go':'go','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RUNTIME_20260901.py':'python','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_RECURSIVE_CLOSURE_MANIFEST_20260901.py':'python','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_PYTHON_ACTUAL_USE_SELFTEST_20260901.py':'python','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json':'json','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py':'python','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json':'json','governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py':'python'}
def fail(c,m):print(f'PRE_LAB_MECHANICAL_GATE_DENIED:{c}:{m}',file=sys.stderr);raise SystemExit(RC)
def data(r):return (ROOT/r).read_bytes()
def gitblob(b):h=hashlib.sha1();h.update(f'blob {len(b)}\0'.encode());h.update(b);return h.hexdigest()
def run(cmd,env=None):
 p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env);sys.stdout.write(p.stdout);sys.stderr.write(p.stderr)
 if p.returncode:fail('BUILD_OR_SYNTAX',f'{cmd[0]}:rc={p.returncode}')
def check_kind(r,w):
 b=data(r);s=b.lstrip()
 try:
  if w=='json':json.loads(b)
  elif w=='python':ast.parse(b.decode(),filename=r)
  elif w=='go' and not s.startswith(b'package main'):fail('GO_CONTENT_TYPE',r)
  elif w=='dockerfile' and not re.search(br'(?m)^FROM\s+',b):fail('DOCKERFILE_CONTENT_TYPE',r)
 except Exception as e:fail('PARSE',f'{r}:{type(e).__name__}')
def main():
 for r,w in EXPECTED.items():
  if not (ROOT/r).is_file():fail('EXPECTED_FILE_MISSING',r)
  check_kind(r,w)
 d=data('.devcontainer/Dockerfile').decode();q=json.loads(data('.devcontainer/devcontainer.json'))
 if q.get('build',{}).get('dockerfile')!='Dockerfile' or q.get('build',{}).get('context')!='..':fail('DEVCONTAINER_BUILD_MAPPING','unexpected')
 for n,l in enumerate(d.splitlines(),1):
  m=re.match(r'^\s*(COPY|ADD)\s+(?:--\S+\s+)*([^\s]+)',l)
  if m and not m.group(2).startswith(('http://','https://','--from=')) and not (ROOT/m.group(2)).is_file():fail('DOCKER_COPY_SOURCE_MISSING',f'{n}:{m.group(2)}')
 for needle in ['multiverse-v36-session-gate-v7r6','build-selftest','MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go','python-actual-use-selftest.py','V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py','rate-budget-history-selftest.py']:
  if needle not in d:fail('DOCKER_V7R6_WIRING',needle)
 gate=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go').decode()
 builder=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py').decode()
 if 'multiverse-v36-session-gate-v7r6' not in builder or 'V19.7.36-v7r6-image-identity' not in builder:fail('IMAGE_IDENTITY_V7R6_WIRING','stale-session-gate-or-version')
 for needle in ['apiHardBudget = 40','apiReserveRemaining = 8','q.Set("since"','cursorOverlap = 2 * time.Second','rate-limited','minute_8_5_requests=24','ten_minute_requests=27','scanStart','scanSince(cursor)','rate-remaining-missing','rate-limit-missing','rate-reset-missing','PAGINATION_RACE_SELFTEST_PASS','RATE_HEADERS_FAIL_CLOSED_SELFTEST_PASS']:
  if needle not in gate:fail('RATE_BUDGET_REMEDIATION_WIRING',needle)
 if 'watermark = d' in gate or 'if d.After(watermark)' in gate:fail('PAGINATION_WATERMARK_REGRESSION','final-page-watermark-present')
 hist=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py').decode()
 for needle in ['range(1,601)','LATE_SECONDS=510','full_used==28','updated_at > since']:
  if needle not in hist:fail('RATE_BUDGET_HISTORY_SELFTEST_WIRING',needle)
 run([sys.executable,'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_RATE_BUDGET_HISTORY_SELFTEST_20260901.py'])
 bnd=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json'))['step3'];pb=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py')
 if bnd['git_blob']!=gitblob(pb) or bnd['sha256']!=hashlib.sha256(pb).hexdigest() or bnd['size']!=len(pb) or bnd.get('mode')!='NONMUTATING' or bnd.get('mutations')!=0:fail('STEP3_BINDING','mismatch')
 a=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R6_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json'))
 if a.get('version')!='V19.7.36-v7r6' or a.get('authority')!='REVIEW_ONLY_NO_LIVE_AUTHORITY' or a.get('runtime')!='OFF':fail('ASSEMBLY_MANIFEST','authority')
 rb=a.get('api_budget_remediation',{})
 if rb.get('hard_process_budget_requests')!=40 or rb.get('rate_limit_remaining_reserve')!=8 or rb.get('poll_interval_seconds')!=30 or rb.get('approval_window_seconds')!=600:fail('ASSEMBLY_RATE_BUDGET','mismatch')
 with tempfile.TemporaryDirectory(prefix='multiverse-prelab-') as td:
  for r,w in EXPECTED.items():
   p=ROOT/r
   if w=='python':py_compile.compile(str(p),cfile=str(pathlib.Path(td)/(p.name+'.pyc')),doraise=True)
   elif w=='go':
    if not shutil.which('go'):fail('GO_TOOL_UNAVAILABLE',r)
    e=dict(os.environ);e['CGO_ENABLED']='0';run(['go','build','-trimpath','-buildvcs=false','-o',str(pathlib.Path(td)/p.stem),str(p)],e)
 wf=data('.github/workflows/multiverse-v36-prelab-exact-image-build.yml').decode()
 if 'workflow_dispatch' in wf:fail('WORKFLOW_DISPATCH_PROHIBITED','present')
 if not shutil.which('docker'):fail('DOCKER_TOOL_UNAVAILABLE','mandatory-final-tree-build-not-run')
 cmd=['docker','build','--progress=plain','--no-cache'];tag=os.environ.get('MULTIVERSE_PRELAB_DOCKER_TAG','').strip()
 if tag:cmd+=['-t',tag]
 cmd+=['-f','.devcontainer/Dockerfile','.'];run(cmd)
 print('REAL_DOCKER_IMAGE_BUILD_PASS');print('PRE_LAB_MECHANICAL_GATE_PASS');print('SECURITY_AUTHORITY_GRANTED=false')
if __name__=='__main__':main()
