from pathlib import Path

path = Path("automation/review_dispatcher_v1/review.py")
text = path.read_text()

helper = '''def _cross_lane_execution_state_valid(
    lab_execution_state: object,
    auditor_execution_state: object,
) -> bool:
    lab_suffix = "_REVIEW_REQUESTED"
    auditor_suffix = "_AUDIT_REQUESTED"
    if not isinstance(lab_execution_state, str):
        return False
    if not isinstance(auditor_execution_state, str):
        return False
    if not lab_execution_state.endswith(lab_suffix):
        return False
    if not auditor_execution_state.endswith(auditor_suffix):
        return False
    lab_family = lab_execution_state[:-len(lab_suffix)]
    auditor_family = auditor_execution_state[:-len(auditor_suffix)]
    return bool(lab_family) and lab_family == auditor_family


'''
needle = "def _check_auditor_upstream(\n"
assert needle in text
text = text.replace(needle, helper + needle, 1)

old = '''        check(
            "upstream_lab_request_execution_state",
            latest_lab_request["execution_state"]
            == job["request"]["execution_state"],
            repr(latest_lab_request["execution_state"]),
        )
'''
new = '''        lab_execution_state = latest_lab_request["execution_state"]
        auditor_execution_state = job["request"]["execution_state"]
        check(
            "upstream_lab_request_execution_state",
            _cross_lane_execution_state_valid(
                lab_execution_state,
                auditor_execution_state,
            ),
            f"lab={lab_execution_state!r} auditor={auditor_execution_state!r}",
        )
'''
assert old in text
text = text.replace(old, new, 1)

old_artifact = '            "execution_state": job["request"]["execution_state"],\n'
new_artifact = '            "execution_state": latest_lab_request.get("execution_state"),\n'
assert old_artifact in text
text = text.replace(old_artifact, new_artifact, 1)
path.write_text(text)
