#!/usr/bin/env python3
"""Review-only pre-Lab mechanical gate. It cannot grant security/audit authority."""
from __future__ import annotations
import ast,hashlib,json,os,pathlib,py_compile,re,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];RC=92
EXPECTED={
'.devcontainer/Dockerfile':'dockerfile','.devcontainer/devcontainer.json':'json','.devcontainer/v19_7_36_requirements.txt':'text',
'.github/workflows/multiverse-v36-prelab-exact-image-build.yml':'text',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_EXTERNAL_SESSION_GATE_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R3_IMAGE_IDENTITY_BUILDER_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_ROOT_ANCHOR_PRODUCER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_CONTROL_PLANE_RUNNER_20260901.go':'go',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RUNTIME_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_RECURSIVE_CLOSURE_MANIFEST_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R2_PYTHON_ACTUAL_USE_SELFTEST_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json':'json',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py':'python',
'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R3_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json':'json'}
def fail(c,m):print(f'PRE_LAB_MECHANICAL_GATE_DENIED:{c}:{m}',file=sys.stderr);raise SystemExit(RC)
def data(r):return (ROOT/r).read_bytes()
def kind(r,b):
 s=b.lstrip()
 if r.endswith('.json'):
  try:json.loads(b)
  except Exception as e:fail('JSON_PARSE',f'{r}:{type(e).__name__}')
  return'json'
 if r.endswith('.py'):
  try:ast.parse(b.decode(),filename=r)
  except Exception as e:fail('PYTHON_PARSE',f'{r}:{type(e).__name__}')
  return'python'
 if r.endswith('.go'):
  if not s.startswith(b'package main'):fail('GO_CONTENT_TYPE',r)
  return'go'
 if pathlib.PurePosixPath(r).name=='Dockerfile':
  if not re.search(br'(?m)^FROM\s+',b):fail('DOCKERFILE_CONTENT_TYPE',r)
  return'dockerfile'
 return'text'
def run(cmd,env=None):
 p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 sys.stdout.write(p.stdout)
 if p.returncode:fail('BUILD_OR_SYNTAX',f'{cmd[0]}:{p.stderr[-1200:]}')
def gitblob(b):h=hashlib.sha1();h.update(f'blob {len(b)}\0'.encode());h.update(b);return h.hexdigest()
def binding():
 q=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json'));s=q['step3'];b=data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py')
 if s['git_blob']!=gitblob(b) or s['sha256']!=hashlib.sha256(b).hexdigest() or s['size']!=len(b) or s.get('mode')!='NONMUTATING' or s.get('mutations')!=0 or s.get('control_runner_action')!='step3-preflight':fail('STEP3_BINDING','mismatch')
def docker_sources():
 for n,l in enumerate(data('.devcontainer/Dockerfile').decode().splitlines(),1):
  m=re.match(r'^\s*(COPY|ADD)\s+(?:--\S+\s+)*([^\s]+)',l)
  if not m:continue
  s=m.group(2)
  if s.startswith(('http://','https://','--from=')):continue
  if any(c in s for c in '*?['):fail('DOCKER_GLOB_UNSUPPORTED',f'{n}:{s}')
  if not (ROOT/s).is_file():fail('DOCKER_COPY_SOURCE_MISSING',f'{n}:{s}')
def main():
 for r,w in EXPECTED.items():
  if not (ROOT/r).is_file():fail('EXPECTED_FILE_MISSING',r)
  g=kind(r,data(r))
  if g!=w:fail('ROLE_CONTENT_MISMATCH',f'{r}:{w}!={g}')
 if data('.devcontainer/Dockerfile').lstrip().startswith(b'{') or data('.devcontainer/devcontainer.json').lstrip().startswith(b'FROM '):fail('ASSEMBLY_SWAP','devcontainer/dockerfile')
 docker_sources();binding()
 with tempfile.TemporaryDirectory(prefix='multiverse-prelab-') as td:
  for r,w in EXPECTED.items():
   p=ROOT/r
   if w=='python':
    try:py_compile.compile(str(p),cfile=str(pathlib.Path(td)/(p.name+'.pyc')),doraise=True)
    except Exception as e:fail('PY_COMPILE',f'{r}:{type(e).__name__}')
   elif w=='go':
    if not shutil.which('go'):fail('GO_TOOL_UNAVAILABLE',r)
    e=dict(os.environ);e['CGO_ENABLED']='0';run(['go','build','-trimpath','-buildvcs=false','-o',str(pathlib.Path(td)/p.stem),str(p)],e)
 q=json.loads(data('.devcontainer/devcontainer.json'))
 if q.get('build',{}).get('dockerfile')!='Dockerfile' or q.get('build',{}).get('context')!='..':fail('DEVCONTAINER_BUILD_MAPPING','unexpected')
 d=data('.devcontainer/Dockerfile').decode()
 for needle in ['multiverse-v36-session-gate-v7r3','multiverse-v36-anchor-v7r2','multiverse-v36-control-v7r2','python-actual-use-selftest.py','image-identity-builder.py','image-identity-v7r3.json']:
  if needle not in d:fail('DOCKER_V7R3_WIRING',needle)
 if 'wake-v7' in d or 'multiverse-v36-trigger-v7r2' in d:fail('SAME_UID_WAKE_REGRESSION','in-container-wake-artifact')
 a=json.loads(data('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R3_CANDIDATE_ASSEMBLY_MANIFEST_20260901.json'))
 x=a.get('external_owner_trigger',{})
 if a.get('version')!='V19.7.36-v7r3' or x.get('generic_codespaces_environment_is_authority') is not False or x.get('candidate_or_same_uid_can_self_issue') is not False:fail('OWNER_TRIGGER_CONTRACT','external-session-binding-required')
 wf=data('.github/workflows/multiverse-v36-prelab-exact-image-build.yml').decode()
 for needle in ['push:','GITHUB_SHA','MULTIVERSE_PRELAB_DOCKER_TAG','PRELAB_FINAL_TREE_DOCKER_BUILD_PASS=true']:
  if needle not in wf:fail('WORKFLOW_CONTRACT',needle)
 if 'workflow_dispatch' in wf:fail('WORKFLOW_DISPATCH_PROHIBITED','present')
 if shutil.which('docker'):
  cmd=['docker','build','--no-cache']
  tag=os.environ.get('MULTIVERSE_PRELAB_DOCKER_TAG','').strip()
  if tag:cmd+=['-t',tag]
  cmd+=['-f','.devcontainer/Dockerfile','.']
  run(cmd);print('REAL_DOCKER_IMAGE_BUILD_PASS')
 else:fail('DOCKER_TOOL_UNAVAILABLE','mandatory-final-tree-build-not-run')
 print('PRE_LAB_MECHANICAL_GATE_PASS');print('SECURITY_AUTHORITY_GRANTED=false')
if __name__=='__main__':main()
