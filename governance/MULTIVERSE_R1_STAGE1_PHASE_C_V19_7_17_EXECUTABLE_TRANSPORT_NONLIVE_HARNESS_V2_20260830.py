#!/usr/bin/env python3
import errno
import fcntl
import hashlib
import importlib.util
import os
import subprocess
import sys

EXPECTED_GENERATOR_BYTES = 3113
EXPECTED_GENERATOR_BLOB = "bebf495c718555ec121eccba133eec86b165687a"
EXPECTED_GENERATOR_SHA256 = "a2e6416ed29a813d3a31e8c53bb379f20ab6a91481fd9ac0c25a13de55b20b2b"

def git_blob_sha1(data):
    hdr=b"blob "+str(len(data)).encode("ascii")+b"\0"
    return hashlib.sha1(hdr+data).hexdigest()

def load_generator(path):
    data=open(path,"rb").read()
    if len(data)!=EXPECTED_GENERATOR_BYTES:
        raise SystemExit("GENERATOR_LENGTH_MISMATCH")
    if git_blob_sha1(data)!=EXPECTED_GENERATOR_BLOB:
        raise SystemExit("GENERATOR_BLOB_MISMATCH")
    if hashlib.sha256(data).hexdigest()!=EXPECTED_GENERATOR_SHA256:
        raise SystemExit("GENERATOR_SHA256_MISMATCH")
    spec=importlib.util.spec_from_file_location("mv_gen",path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def static_generator_binding_checks(mod):
    new=mod.NEW
    required=[
        b'os.memfd_create(',
        b'os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING',
        b'fcntl.F_ADD_SEALS',
        b'fcntl.F_GET_SEALS',
        b'fcntl.F_SEAL_WRITE',
        b'snap=os.pread(fd,5303,0)',
        b'hashlib.sha1(hdr+snap).hexdigest()',
        b'"fe51117fd3fcaa41537b5f92c84841716af27f74"',
        b'"248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e"',
        b'p=f"/proc/self/fd/{fd}"',
        b'pass_fds=(fd,)',
    ]
    for token in required:
        if token not in new:
            raise SystemExit("MISSING_REQUIRED_TOKEN:"+token.decode("ascii","replace"))
    if new.count(b'parse=subprocess.run(')!=1:
        raise SystemExit("PARSE_SITE_COUNT_MISMATCH")
    if new.count(b'run=subprocess.run(')!=1:
        raise SystemExit("RUN_SITE_COUNT_MISMATCH")
    if new.count(b'p=f"/proc/self/fd/{fd}"')!=1:
        raise SystemExit("PROC_FD_BINDING_COUNT_MISMATCH")
    forbidden=[b'os.unlink(',b'os.rename(',b'os.replace(',b'open(p,"wb"',b'open(p,\'wb\'']
    for token in forbidden:
        if token in new:
            raise SystemExit("FORBIDDEN_POST_BINDING_PRIMITIVE:"+token.decode("ascii","replace"))

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
        os.pwrite(fd,b"X",0)
        raise SystemExit("SEALED_WRITE_UNEXPECTEDLY_SUCCEEDED")
    except OSError as e:
        if e.errno!=errno.EPERM:
            raise
    snap=os.pread(fd,len(payload)+1,0)
    if snap!=payload:
        raise SystemExit("SNAPSHOT_MISMATCH")
    os.set_inheritable(fd,True)
    p=f"/proc/self/fd/{fd}"
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
    static_generator_binding_checks(mod)
    dynamic_memfd_probe()
    print("V19_7_17_NONLIVE_OBJECT_BINDING_HARNESS_PASS")

if __name__=="__main__":
    main()
