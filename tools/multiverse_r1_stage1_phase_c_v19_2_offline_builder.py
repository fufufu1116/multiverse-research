#!/usr/bin/env python3
"""v19.3 review-only OFFLINE builder. No network imports/calls. Emits bytes only."""
import argparse,base64,hashlib,json,re
STEP1_LEN=4687; STEP1_SHA='bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74'; B64_LEN=6252; B64_SHA='f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2'
INIT_LEN=4291; INIT_SHA='3f21f89884757dab2728d4be376f19a2bbe4aa3396162434e1822ce2b36375d2'; TEMPLATE_LEN=382; TEMPLATE_SHA='7346430c248d0e9f3eed92c7fda4cb1abc342fb7a7a803467afcbfc3f899f15e'; ASSEMBLE_LEN=293; ASSEMBLE_SHA='909df243fbf0e31adcbc2de8018796ee2a4aa5fb1fb8bce58c3872b5ef74f871'; SOURCE_LEN=1716; SOURCE_SHA='cb34865720b2973b1226b8afa81074098c246c1308d0797da29490df6f251ecd'
CH=('6e1ca4a34325f5cc8169f8a48100c1f0db46ed5ed2b3ebc3e03b6a3ace8494bd','2cb9655f64eacf65ebbf7df0db10021626ffcfecc4c286bcb7c090cd9f95d09f','cb0a608788378b2778a6f498089f09d445cc55d5c4d5c3688c9a7fd2aa1d334a','a82ff588dbf023634b91caa138186e6b9dacd8049cd8147de20ef2f5b2375ae4','cf498ec4bf0188455fa4386eaaf96388d1d0936e76edad9186c6d5bd4a2b51a4','6176a57e1829d53e12cbaa7e898226cc4b1eaca48778dbc39bcf0d9b593e1ec1','d2e1df752ec73d10662009b38f18dcb5316f7443de22d6fba9dfcceaf7c9858d','90b25ed739ea8a4727fb13320a9038ed48951f55718bd7c1722c4927e9ad1eb3','3e6b2a2f38bc8c0caf614a483787552eced3b9e563c32053ea897827a5b87316','243fa4861f7e83f49f85dbeb495ea03775465b271559dea66ae89d82c72562e8','a1b4e5504f45b919d62a554fce54567b762f754be2b5abc50b4dab2c1b94f869','4c641d73dbb4c5c0af380182dcce508ff6c6b888bf27c0fdbd5528f104b97592','9c7e90df065e8c28ce6b236253994244a9e68fdebf877ae8020535c1e9b04b77')
def sha(x):return hashlib.sha256(x).hexdigest()
def text(p):return open(p,'r',encoding='utf-8').read()
def body(p):
 s=text(p)
 try:
  x=json.loads(s)
 except json.JSONDecodeError:
  return s
 if isinstance(x,dict) and isinstance(x.get('body'),str): return x['body']
 return s
def cands(s):return re.findall(r'`([A-Za-z0-9+/=]{40,})`',s)
def exact(s,n,h):
 c=cands(s)
 for i in range(len(c)):
  z=''
  for j in range(i,min(len(c),i+16)):
   z+=c[j]
   try:x=base64.b64decode(z,validate=True)
   except Exception:continue
   if len(x)==n and sha(x)==h:return x.decode()
 raise SystemExit('missing exact authoritative action '+h)
def step1(g):
 d=json.loads(text(g));src=d['literal_sequence']['step1_define_external_verifier_bootstrap_and_preauth'];m='phase_c_bootstrap\nPHASE_C_BOOTSTRAP_RC=$?'
 if src.count(m)!=1:raise SystemExit('Step1 marker mismatch')
 i=src.index(m);tail='''phase_c_bootstrap
PHASE_C_BOOTSTRAP_RC=$?
if [ "$PHASE_C_BOOTSTRAP_RC" -ne 0 ]; then command printf '%s\\n' "PHASE_C_EXTERNAL_BOOTSTRAP_FAILED_RC=$PHASE_C_BOOTSTRAP_RC" >&2; exit 90; fi
command printf '%s\\n' 'PHASE_C_EXTERNAL_BOOTSTRAP_PASS'
phase_c_verify
PHASE_C_PREAUTH_VERIFY_RC=$?
if [ "$PHASE_C_PREAUTH_VERIFY_RC" -ne 0 ]; then command printf '%s\\n' "PHASE_C_EXTERNAL_VERIFY_BEFORE_PREAUTH_FAILED_RC=$PHASE_C_PREAUTH_VERIFY_RC" >&2; exit 91; fi
command printf '%s\\n' 'PHASE_C_EXTERNAL_VERIFY_BEFORE_PREAUTH_PASS'
( cd "$EXEC_ROOT" && exec python -B tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py --preauth )
PHASE_C_PREAUTH_RC=$?
if [ "$PHASE_C_PREAUTH_RC" -ne 0 ]; then command printf '%s\\n' "PHASE_C_PREAUTH_COMMAND_FAILED_RC=$PHASE_C_PREAUTH_RC" >&2; exit 92; fi
unset PHASE_C_BOOTSTRAP_RC PHASE_C_PREAUTH_VERIFY_RC PHASE_C_PREAUTH_RC
command printf '%s\\n' 'PHASE_C_EXTERNAL_BOOTSTRAP_AND_PREAUTH_PASS'
''';x=(src[:i]+tail).encode()
 if len(x)!=STEP1_LEN or sha(x)!=STEP1_SHA:raise SystemExit('Step1 invariant mismatch')
 return x
def main():
 p=argparse.ArgumentParser();p.add_argument('--part-a',required=True);p.add_argument('--part-b',required=True);p.add_argument('--gate',required=True);a=p.parse_args()
 A=body(a.part_a);B=body(a.part_b);init=exact(A,INIT_LEN,INIT_SHA);t=exact(A,TEMPLATE_LEN,TEMPLATE_SHA);assemble=exact(B,ASSEMBLE_LEN,ASSEMBLE_SHA);source=exact(B,SOURCE_LEN,SOURCE_SHA)
 for k,n in {'__CHUNK__':1,'__INDEX__':4}.items():
  if t.count(k)!=n:raise SystemExit('placeholder cardinality mismatch '+k)
 sb=base64.b64encode(step1(a.gate)).decode()
 if len(sb)!=B64_LEN or sha(sb.encode())!=B64_SHA:raise SystemExit('base64 invariant mismatch')
 chunks=[sb[i:i+512] for i in range(0,len(sb),512)];actions=[init]
 if len(chunks)!=13:raise SystemExit('chunk count mismatch')
 for n,c in enumerate(chunks):
  ln=108 if n==12 else 512
  if len(c)!=ln or sha(c.encode())!=CH[n]:raise SystemExit('chunk invariant mismatch')
  act=t.replace('__CHUNK__',c).replace('__INDEX__',f'{n:02d}')
  if '__CHUNK__' in act or '__INDEX__' in act:raise SystemExit('unreplaced placeholder')
  if len(act.encode())!=(453 if n==12 else 857):raise SystemExit('concrete chunk action length mismatch')
  actions.append(act)
 actions += [assemble,source]
 out='; '.join('eval "$(printf %s '+base64.b64encode(x.encode()).decode()+' | base64 -d)" || exit $?' for x in actions)
 print(out,end='')
if __name__=='__main__':main()
