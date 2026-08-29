#!/usr/bin/env python3
"""Phase C v18 review-only single-paste candidate.
Compress operator interaction, never the authoritative Step1 state machine.
DRAFT / REVIEW ONLY / NOT LIVE AUTHORITY. Runtime OFF.
"""
import base64,hashlib,json,re,urllib.request
PART_A=5420731105; PART_B=5420744033
API='https://api.github.com/repos/fufufu1116/multiverse-research/issues/comments/{}'
STEP1_LEN=4687; STEP1_SHA='bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74'; B64_LEN=6252; B64_SHA='f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2'
INIT_LEN=2314; INIT_SHA='36259d43cea843a2d7cbac981b133f576149cc71f11177dd6b6de544872d31ed'; TEMPLATE_LEN=4155; TEMPLATE_SHA='5e9c26723e9d04bb65abd4917fd02e25d4e42c2ffc1b9eb052202bf3e649cdee'; ASSEMBLE_LEN=4839; ASSEMBLE_SHA='f84b9f18a33c66eaf49475491be8baca63e03dc752ef31432cdec7c50950ed31'; SOURCE_LEN=7000; SOURCE_SHA='566669bb53f693bb380598fcf0e6d25b20b79987e5d8abc3869ffe3e3ae7b109'
CHUNK_HASHES=('6e1ca4a34325f5cc8169f8a48100c1f0db46ed5ed2b3ebc3e03b6a3ace8494bd','2cb9655f64eacf65ebbf7df0db10021626ffcfecc4c286bcb7c090cd9f95d09f','cb0a608788378b2778a6f498089f09d445cc55d5c4d5c3688c9a7fd2aa1d334a','a82ff588dbf023634b91caa138186e6b9dacd8049cd8147de20ef2f5b2375ae4','cf498ec4bf0188455fa4386eaaf96388d1d0936e76edad9186c6d5bd4a2b51a4','6176a57e1829d53e12cbaa7e898226cc4b1eaca48778dbc39bcf0d9b593e1ec1','d2e1df752ec73d10662009b38f18dcb5316f7443de22d6fba9dfcceaf7c9858d','90b25ed739ea8a4727fb13320a9038ed48951f55718bd7c1722c4927e9ad1eb3','3e6b2a2f38bc8c0caf614a483787552eced3b9e563c32053ea897827a5b87316','243fa4861f7e83f49f85dbeb495ea03775465b271559dea66ae89d82c72562e8','a1b4e5504f45b919d62a554fce54567b762f754be2b5abc50b4dab2c1b94f869','4c641d73dbb4c5c0af380182dcce508ff6c6b888bf27c0fdbd5528f104b97592','9c7e90df065e8c28ce6b236253994244a9e68fdebf877ae8020535c1e9b04b77')
def sha(b): return hashlib.sha256(b).hexdigest()
def body(cid):
 r=urllib.request.Request(API.format(cid),headers={'Accept':'application/vnd.github+json','User-Agent':'multiverse-v18-review-candidate'}); return json.load(urllib.request.urlopen(r,timeout=20))['body']
def pieces(t,p,n):
 o=[]
 for i in range(1,n+1):
  m=re.search(r'`%s%d`:\s*\n`([A-Za-z0-9+/=]+)`'%(p,i),t)
  if not m: raise SystemExit('missing manifest piece')
  o.append(m.group(1))
 return ''.join(o)
def dec(s,n,h):
 b=base64.b64decode(s,validate=True)
 if len(b)!=n or sha(b)!=h: raise SystemExit('authoritative action invariant mismatch')
 return b.decode()
def main():
 a,b=body(PART_A),body(PART_B); init=dec(pieces(a,'I',3),INIT_LEN,INIT_SHA); template=dec(pieces(a,'C',5),TEMPLATE_LEN,TEMPLATE_SHA); assemble=dec(pieces(b,'A',6),ASSEMBLE_LEN,ASSEMBLE_SHA); source=dec(pieces(b,'S',8),SOURCE_LEN,SOURCE_SHA)
 u='https://raw.githubusercontent.com/fufufu1116/multiverse-research/19a14cfd019cceab199571b5d03d4dd0ba5bcd22/governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRODUCTION_EXECUTION_OWNER_GATE_CANDIDATE_20260824_v1.json'; gate=json.load(urllib.request.urlopen(u,timeout=20)); src=gate['literal_sequence']['step1_define_external_verifier_bootstrap_and_preauth']; marker='phase_c_bootstrap\nPHASE_C_BOOTSTRAP_RC=$?'
 if src.count(marker)!=1: raise SystemExit('Step1 reconstruction marker mismatch')
 i=src.index(marker); tail='''phase_c_bootstrap
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
'''; step1=(src[:i]+tail).encode()
 if len(step1)!=STEP1_LEN or sha(step1)!=STEP1_SHA: raise SystemExit('Step1 invariant mismatch')
 sb64=base64.b64encode(step1).decode()
 if len(sb64)!=B64_LEN or sha(sb64.encode())!=B64_SHA: raise SystemExit('Step1 base64 invariant mismatch')
 chunks=[sb64[x:x+512] for x in range(0,len(sb64),512)]; actions=[init]
 if len(chunks)!=13: raise SystemExit('chunk count mismatch')
 for n,c in enumerate(chunks):
  ln=108 if n==12 else 512
  if len(c)!=ln or sha(c.encode())!=CHUNK_HASHES[n]: raise SystemExit('chunk invariant mismatch')
  act=template; vals={'__CHUNK__':c,'__INDEX__':f'{n:02d}','__EXPECTED_LENGTH__':str(ln),'__EXPECTED_SHA256__':CHUNK_HASHES[n]}
  for k,v in vals.items():
   if act.count(k)!=1: raise SystemExit('template placeholder cardinality mismatch')
   act=act.replace(k,v)
  actions.append(act)
 actions += [assemble,source]
 # Base64 wrappers preserve every authoritative action byte exactly while the outer
 # result is one shell line. Failure is terminal before the next state transition.
 wrapped=[]
 for x in actions:
  q=base64.b64encode(x.encode()).decode(); wrapped.append('eval "$(printf %s '+q+' | base64 -d)" || exit $?')
 print('; '.join(wrapped),end='')
if __name__=='__main__': main()
