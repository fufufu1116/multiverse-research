from pathlib import Path

path = Path("automation/review_dispatcher_v1/test_integrated_resilience_convergence_v1.py")
text = path.read_text()
old = '        "execution_state": "TEST_REQUESTED",\n'
new = '        "execution_state": ("TEST_REVIEW_REQUESTED" if lane == "LAB" else "TEST_AUDIT_REQUESTED"),\n'
assert old in text
path.write_text(text.replace(old, new, 1))
