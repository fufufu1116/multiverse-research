from __future__ import annotations

REQUIRED_ARTIFACT_KEYS = {
    'lane','reviewed_repo','reviewed_pr','reviewed_head','reviewed_base','reviewed_main',
    'request_id','evidence_refs','verdict','producer_marker','proof_ceiling'
}

VALID_LANES = {'INDEPENDENT_LAB','INDEPENDENT_AUDITOR'}
VALID_VERDICTS = {'PASS','FIX_REQUIRED'}


def _artifact_shape_ok(a):
    return isinstance(a, dict) and set(a) == REQUIRED_ARTIFACT_KEYS and a['lane'] in VALID_LANES and a['verdict'] in VALID_VERDICTS


def lab_gate(*, current, lab_artifact, candidate_producer_marker):
    if not _artifact_shape_ok(lab_artifact):
        return False
    if lab_artifact['lane'] != 'INDEPENDENT_LAB':
        return False
    if lab_artifact['producer_marker'] == candidate_producer_marker:
        return False
    return (
        lab_artifact['reviewed_repo'] == current['repo'] and
        lab_artifact['reviewed_pr'] == current['pr'] and
        lab_artifact['reviewed_head'] == current['head'] and
        lab_artifact['reviewed_base'] == current['base'] and
        lab_artifact['reviewed_main'] == current['main']
    )


def auditor_gate(*, current, lab_artifact, auditor_artifact, candidate_producer_marker):
    if not lab_gate(current=current, lab_artifact=lab_artifact, candidate_producer_marker=candidate_producer_marker):
        return False
    if lab_artifact['verdict'] != 'PASS':
        return False
    if not _artifact_shape_ok(auditor_artifact) or auditor_artifact['lane'] != 'INDEPENDENT_AUDITOR':
        return False
    if auditor_artifact['producer_marker'] in {candidate_producer_marker, lab_artifact['producer_marker']}:
        return False
    if auditor_artifact['request_id'] != lab_artifact['request_id']:
        return False
    return (
        auditor_artifact['reviewed_repo'] == current['repo'] and
        auditor_artifact['reviewed_pr'] == current['pr'] and
        auditor_artifact['reviewed_head'] == current['head'] and
        auditor_artifact['reviewed_base'] == current['base'] and
        auditor_artifact['reviewed_main'] == current['main']
    )
