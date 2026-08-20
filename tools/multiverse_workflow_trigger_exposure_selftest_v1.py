#!/usr/bin/env python3
from multiverse_workflow_trigger_exposure_v1 import event_blocks, classify_event


def exposure(text,path,event):
    blocks=event_blocks(text)
    assert event in blocks,(event,blocks)
    return classify_event(path,event,blocks[event])['exposure']


def main():
    p='.github/workflows/x.yml'
    assert exposure("name: x\non:\n  push:\n    paths: ['.github/workflows/x.yml']\n",p,'push')=='SELF_FILE_ONLY'
    assert exposure("name: x\non:\n  push:\n    paths:\n      - 'tools/**'\n",p,'push')=='RESTRICTED_PATHS'
    assert exposure("name: x\non:\n  push:\n    branches: [main]\n",p,'push')=='ANY_PATH'
    assert exposure("name: x\non:\n  pull_request:\n",p,'pull_request')=='ANY_PR_PATH'
    assert exposure("name: x\non:\n  pull_request:\n    paths: ['governance/**']\n",p,'pull_request')=='PR_RESTRICTED_PATHS'
    assert exposure("name: x\non:\n  schedule:\n    - cron: '0 0 * * *'\n",p,'schedule')=='SCHEDULED'
    assert exposure("name: x\non:\n  workflow_dispatch:\n",p,'workflow_dispatch')=='MANUAL_ONLY'
    print('MULTIVERSE_WORKFLOW_TRIGGER_EXPOSURE_SELFTEST_PASS')

if __name__=='__main__': main()
