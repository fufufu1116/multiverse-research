#!/usr/bin/env python3
"""Selftest for workflow trigger inventory scanner."""
from multiverse_workflow_trigger_inventory_v1 import parse_events, classify

def check(text, expected_events, expected_class):
    p = parse_events(text)
    assert p['events'] == sorted(expected_events), (p, expected_events)
    assert classify(p['events'], p['parse_status']) == expected_class, (p, expected_class)

def main():
    check("name: x\non:\n  workflow_dispatch:\n", ['workflow_dispatch'], 'MANUAL_ONLY')
    check("name: x\non:\n  push:\n    branches: [main]\n  workflow_dispatch:\n", ['push','workflow_dispatch'], 'AUTO_TRIGGER_PRESENT')
    check("name: x\non: [push, pull_request]\n", ['pull_request','push'], 'AUTO_TRIGGER_PRESENT')
    check("name: x\non:\n  schedule:\n    - cron: '0 0 * * *'\n", ['schedule'], 'AUTO_TRIGGER_PRESENT')
    check("name: x\non:\n  workflow_call:\n", ['workflow_call'], 'CALLABLE_NOT_STANDALONE_MANUAL')
    p = parse_events("name: x\njobs: {}\n")
    assert classify(p['events'], p['parse_status']) == 'UNKNOWN_FAIL_CLOSED'
    p = parse_events("name: x\non:\n  magic_future_event:\n")
    assert classify(p['events'], p['parse_status']) == 'UNKNOWN_FAIL_CLOSED'
    print('MULTIVERSE_WORKFLOW_TRIGGER_INVENTORY_SELFTEST_PASS')

if __name__ == '__main__':
    main()
