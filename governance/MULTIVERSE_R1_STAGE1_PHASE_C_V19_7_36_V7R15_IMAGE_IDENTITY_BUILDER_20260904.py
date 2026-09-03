#!/usr/bin/env python3
import hashlib,json,os
OUT='/opt/multiverse/v36/image-identity-v7r3.json'
PATHS=[
'/usr/local/sbin/multiverse-v36-session-gate-v7r7',
'/usr/local/bin/multiverse-v36-arm-v7r7',
'/usr/local/bin/multiverse-v36-ui-ready-v7r7',
'/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7',
'/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r15',
'/usr/local/bin/multiverse-v36-prearm-rate-sanitizer-v7r9',
'/usr/local/bin/multiverse-v36-prearm-rate-readiness-v7r9',
'/usr/local/sbin/multiverse-v36-anchor-v7r2',
'/usr/local/sbin/multiverse-v36-control-v7r2',
'/opt/multiverse/v36/runtime-v7.py',
'/opt/multiverse/v36/step3-binding.json',
'/opt/multiverse/v36/step3.py',
'/opt/multiverse/v36/closure-manifest-v7.json',
]
def ident(p):
 h=hashlib.sha256();n=0
 with open(p,'rb',buffering=0) as f:
  for b in iter(lambda:f.read(1<<20),b''):
   n+=len(b);h.update(b)
 return {'path':p,'size':n,'sha256':h.hexdigest()}
def main():
 body={
  'version':'V19.7.36-v7r15-image-identity',
  'authority_model':'SEALED_MEMFD_INHERITED_TO_PROTECTED_GUARD_THEN_IRREVERSIBLE_USER_DROP',
  'launcher_contract':{
   'path':'/usr/local/bin/multiverse-v36-prearm-rate-sanitizer-v7r9',
   'owner_uid':0,'mode':'4555','authority_uid':64173,
   'authority_uid_owns_runtime_objects':False,
   'no_new_privs_before_probe_exec':True,'fixed_probe_exec':True,
  },
  'guard_contract':{
   'path':'/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r15',
   'owner_uid':0,'mode':'0555','setuid':False,
   'startup_requires_ruid_user_euid_suid_64173':True,
   'sealed_authority_fd_required':True,
   'irreversible_real_user_drop_before_helper_exec':True,
   'helper_path':'/usr/local/bin/multiverse-v36-ui-ready-v7r7',
  },
  'objects':[ident(p) for p in PATHS],
 }
 b=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
 with open(OUT,'wb') as f:f.write(b)
 os.chown(OUT,0,0);os.chmod(OUT,0o444)
 print('PHASE_C_V19_7_36_V7R15_IMAGE_IDENTITY_SHA256='+hashlib.sha256(b).hexdigest())
if __name__=='__main__':main()
