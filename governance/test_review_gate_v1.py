import unittest

from review_gate_v1 import lab_gate, auditor_gate

CURRENT = {
    'repo': 'fufufu1116/multiverse-research',
    'pr': 91,
    'head': '61f4e330fd5b1945dbfbceb223cbc71d205860f2',
    'base': '04a8234096ad6cb98ac0219e25ba6ecffd0823c3',
    'main': '040d37f0a4e426cf2e119706484c90cbb48f0e56',
}


def artifact(lane, verdict='PASS', producer='lab-process', request_id='req-1'):
    return {
        'lane': lane,
        'reviewed_repo': CURRENT['repo'],
        'reviewed_pr': CURRENT['pr'],
        'reviewed_head': CURRENT['head'],
        'reviewed_base': CURRENT['base'],
        'reviewed_main': CURRENT['main'],
        'request_id': request_id,
        'evidence_refs': ['e1'],
        'verdict': verdict,
        'producer_marker': producer,
        'proof_ceiling': 'NO_MERGE_NO_RUNTIME',
    }


class ReviewGateV1Tests(unittest.TestCase):
    def test_exact_head_lab_passes_when_producer_is_distinct(self):
        self.assertTrue(lab_gate(current=CURRENT, lab_artifact=artifact('INDEPENDENT_LAB'), candidate_producer_marker='candidate-process'))

    def test_stale_head_lab_pass_fails_closed(self):
        stale = artifact('INDEPENDENT_LAB')
        stale['reviewed_head'] = '0' * 40
        self.assertFalse(lab_gate(current=CURRENT, lab_artifact=stale, candidate_producer_marker='candidate-process'))

    def test_candidate_cannot_self_manufacture_lab_independence(self):
        a = artifact('INDEPENDENT_LAB', producer='candidate-process')
        self.assertFalse(lab_gate(current=CURRENT, lab_artifact=a, candidate_producer_marker='candidate-process'))

    def test_auditor_requires_exact_current_lab_pass(self):
        lab = artifact('INDEPENDENT_LAB', producer='lab-process', request_id='req-1')
        auditor = artifact('INDEPENDENT_AUDITOR', producer='audit-process', request_id='req-1')
        self.assertTrue(auditor_gate(current=CURRENT, lab_artifact=lab, auditor_artifact=auditor, candidate_producer_marker='candidate-process'))
        lab['reviewed_head'] = 'f' * 40
        self.assertFalse(auditor_gate(current=CURRENT, lab_artifact=lab, auditor_artifact=auditor, candidate_producer_marker='candidate-process'))

    def test_auditor_must_be_distinct_from_lab_and_candidate(self):
        lab = artifact('INDEPENDENT_LAB', producer='lab-process')
        same_as_lab = artifact('INDEPENDENT_AUDITOR', producer='lab-process')
        same_as_candidate = artifact('INDEPENDENT_AUDITOR', producer='candidate-process')
        self.assertFalse(auditor_gate(current=CURRENT, lab_artifact=lab, auditor_artifact=same_as_lab, candidate_producer_marker='candidate-process'))
        self.assertFalse(auditor_gate(current=CURRENT, lab_artifact=lab, auditor_artifact=same_as_candidate, candidate_producer_marker='candidate-process'))


if __name__ == '__main__':
    unittest.main()
