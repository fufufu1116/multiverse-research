#!/usr/bin/env python3
from __future__ import annotations
import unittest
from multiverse_fresh_manifest_v1 import FreshReadError, build_snapshot

H="1"*40
T="2"*40
M="3"*40
MT="4"*40

class Fake:
    def __init__(self, drift=False):
        self.drift=drift
        self.urls=[]
    def __call__(self,u):
        self.urls.append(u)
        if u.endswith("/git/ref/heads/main"): return {"object":{"sha":M}}
        if "/git/ref/heads/agent%2Fexample" in u: return {"object":{"sha":("9"*40 if self.drift else H)}}
        if u.endswith("/git/commits/"+M): return {"tree":{"sha":MT}}
        if u.endswith("/git/commits/"+H): return {"tree":{"sha":T}}
        if u.endswith("/pulls/74"):
            return {"number":74,"state":"open","draft":True,"merged":False,"base":{"ref":"main","sha":M},"head":{"ref":"stale-aggregate","sha":"8"*40},"updated_at":"2026-09-01T00:00:00Z"}
        if u.endswith("/issues/comments/123"):
            return {"id":123,"created_at":"a","updated_at":"a","user":{"login":"owner"},"author_association":"OWNER","performed_via_github_app":{"slug":"chatgpt-codex-connector"},"body":"PASS"}
        raise AssertionError(u)

class Tests(unittest.TestCase):
    def task(self):
        return {"canonical_repo":"fufufu1116/multiverse-research","target_branch":"agent/example","target_head":H,"authority":{"runtime":"OFF"}}
    def test_snapshot(self):
        f=Fake()
        s=build_snapshot(self.task(),74,[123],f)
        self.assertEqual((s["canonical_main"],s["canonical_main_tree"]),(M,MT))
        self.assertEqual((s["target_head"],s["target_tree"]),(H,T))
        self.assertTrue(s["pr"]["draft"])
        self.assertEqual(s["comments"][0]["github_app_slug"],"chatgpt-codex-connector")
        self.assertIn("/git/ref/heads/agent%2Fexample",f.urls[1])
    def test_target_drift_fail_closed(self):
        with self.assertRaises(FreshReadError):
            build_snapshot(self.task(),fetch=Fake(drift=True))
    def test_bad_repo_denied(self):
        t=self.task();t["canonical_repo"]="bad"
        with self.assertRaises(FreshReadError):
            build_snapshot(t,fetch=Fake())

if __name__=="__main__": unittest.main()
