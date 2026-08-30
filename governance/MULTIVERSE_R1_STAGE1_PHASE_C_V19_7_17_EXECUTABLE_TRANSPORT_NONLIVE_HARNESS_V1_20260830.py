#!/usr/bin/env python3
import errno
import fcntl
import importlib.util
import os
import subprocess
import sys

EXPECTED_GENERATOR_BLOB = "2c53205524814a4030e8183d59ce79058346e136"
REQUIRED_TOKENS = [
    b'os.memfd_create(',
    b'os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING',
    b'fcntl.F_ADD_SEALS',
    b'fcntl.F_GET_SEALS',
    b'fcntl.F_SEAL_WRITE',
    b'p=f"/proc/self/fd/{fd}"',
    b'input=snap',
    b'"fe51117fd3fcaa41537b5f92c84841716af27f74"',
    b'"248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e"',
    b'pass_fds=(fd,)',
]

def load_generator(path):
    spec=importlib.util.spec_from_file_location("mv_gen",path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def dynamic_memfd_probe():
    payload=b'printf "V19_7_17_NONLIVE_MEMFD_BINDING_PASS\\n"\n'
    fd=os.memfd_create("mv-v19-7-17-nonlive-proof",os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
    if os.write(fd,payload)!=len(payload):
        raise SystemExit("SHORT_WRITE")
    os.lseek(fd,0,os.SEEK_SET)
    seals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
    fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
    if fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=seals:
        raise SystemExit("SEAL_MISMATCH")
    try:
        os.write(fd,b"X")
        raise SystemExit("SEALED_WRITE_UNEXPECTEDLY_SUCCEEDED")
    except OSError as e:
        if e.errno!=errno.EPERM:
            raise
    os.set_inheritable(fd,True)
    p=f"/proc/self/fd/{fd}"
    with open(p,"rb",buffering=0) as r:
        if r.read()!=payload:
            raise SystemExit("SNAPSHOT_MISMATCH")
    parse=subprocess.run(["/bin/bash","--noprofile","--norc","-n",p],pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if parse.returncode:
        raise SystemExit("PARSE_FAIL")
    run=subprocess.run(["/bin/bash","--noprofile","--norc",p],pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if run.returncode or run.stdout!=b"V19_7_17_NONLIVE_MEMFD_BINDING_PASS\n":
        raise SystemExit("EXEC_BINDING_FAIL")

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: harness.py GENERATOR.py")
    mod=load_generator(sys.argv[1])
    new=mod.NEW
    for token in REQUIRED_TOKENS:
        if token not in new:
            raise SystemExit("MISSING_REQUIRED_TOKEN:"+token.decode("ascii","replace"))
    if new.count(b'parse=subprocess.run(')!=1 or new.count(b'run=subprocess.run(')!=1:
        raise SystemExit("PARSE_RUN_SITE_COUNT_MISMATCH")
    if new.count(b'p=f"/proc/self/fd/{fd}"')!=1:
        raise SystemExit("PROC_FD_BINDING_COUNT_MISMATCH")
    if b'open(p,"wb"' in new or b'os.unlink(' in new or b'os.rename(' in new or b'os.replace(' in new:
        raise SystemExit("POST_BINDING_MUTATION_PRIMITIVE_PRESENT")
    dynamic_memfd_probe()
    print("V19_7_17_NONLIVE_OBJECT_BINDING_HARNESS_PASS")

if __name__=="__main__":
    main()
