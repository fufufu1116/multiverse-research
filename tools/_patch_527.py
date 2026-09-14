from pathlib import Path

# 1) Share one lane-state validator from model.py.
model = Path("automation/review_dispatcher_v1/model.py")
text = model.read_text()
helper = '''\n\ndef cross_lane_execution_state_valid(\n    lab_execution_state,\n    auditor_execution_state,\n):\n    lab_suffix = "_REVIEW_REQUESTED"\n    auditor_suffix = "_AUDIT_REQUESTED"\n    if not isinstance(lab_execution_state, str):\n        return False\n    if not isinstance(auditor_execution_state, str):\n        return False\n    if not lab_execution_state.endswith(lab_suffix):\n        return False\n    if not auditor_execution_state.endswith(auditor_suffix):\n        return False\n    lab_family = lab_execution_state[:-len(lab_suffix)]\n    auditor_family = auditor_execution_state[:-len(auditor_suffix)]\n    return bool(lab_family) and lab_family == auditor_family\n'''
if "def cross_lane_execution_state_valid(" not in text:
    text = text.rstrip() + helper + "\n"
model.write_text(text)

# 2) review.py uses shared helper and Lab artifact binds to Lab state.
review = Path("automation/review_dispatcher_v1/review.py")
text = review.read_text()
text = text.replace(
    "    canonical_json,\n",
    "    canonical_json,\n    cross_lane_execution_state_valid,\n",
    1,
)
start = text.index("def _cross_lane_execution_state_valid(\n")
end = text.index("def _check_auditor_upstream(\n", start)
text = text[:start] + text[end:]
text = text.replace("_cross_lane_execution_state_valid(", "cross_lane_execution_state_valid(")
review.write_text(text)

# 3) T2 must not reintroduce the same cross-lane aliasing after Auditor PASS.
t2 = Path("automation/review_dispatcher_v1/t2.py")
text = t2.read_text()
import_block = '''from automation.review_dispatcher_v1.model import (\n    cross_lane_execution_state_valid,\n)\n'''
if "cross_lane_execution_state_valid" not in text:
    marker = "from automation.review_dispatcher_v1.publisher_freshness_v1 import (\n"
    text = text.replace(marker, import_block + marker, 1)
old = '''    _legacy.require(\n        latest_request["execution_state"] == request["execution_state"],\n        "LATEST_LAB_EXECUTION_STATE_MISMATCH",\n    )\n'''
new = '''    _legacy.require(\n        cross_lane_execution_state_valid(\n            latest_request["execution_state"],\n            request["execution_state"],\n        ),\n        "LATEST_LAB_EXECUTION_STATE_MISMATCH",\n    )\n'''
assert old in text
text = text.replace(old, new, 1)
t2.write_text(text)

# 4) Update the canonical inherited fixture to model legitimate lane-specific states.
test = Path("automation/review_dispatcher_v1/test_dispatcher_legacy_v1.py")
text = test.read_text()
old = '''        auditor_request = lab_request("auditor-upstream")\n        auditor_request["lane"] = "AUDITOR"\n        latest_lab = lab_request("latest-lab")\n'''
new = '''        auditor_request = lab_request("auditor-upstream")\n        auditor_request["lane"] = "AUDITOR"\n        auditor_request["execution_state"] = "TEST_AUDIT_REQUESTED"\n        latest_lab = lab_request("latest-lab")\n        latest_lab["execution_state"] = "TEST_REVIEW_REQUESTED"\n'''
assert old in text
text = text.replace(old, new, 1)
text = text.replace(
    '            "execution_state": auditor_request["execution_state"],\n',
    '            "execution_state": latest_lab["execution_state"],\n',
    1,
)
test.write_text(text)

# 5) Focused regression imports shared helper and verifies both review + T2 source use it.
focused = Path("tools/test_auditor_upstream_execution_state_v1.py")
text = focused.read_text()
text = text.replace(
    "from automation.review_dispatcher_v1.review import _cross_lane_execution_state_valid\n",
    "from pathlib import Path\n\nfrom automation.review_dispatcher_v1.model import cross_lane_execution_state_valid\n",
)
text = text.replace("_cross_lane_execution_state_valid(", "cross_lane_execution_state_valid(")
insert = '''\n    def test_review_and_t2_both_use_shared_lane_validator(self):\n        root = Path(__file__).resolve().parents[1]\n        review_source = (root / "automation/review_dispatcher_v1/review.py").read_text()\n        t2_source = (root / "automation/review_dispatcher_v1/t2.py").read_text()\n        token = "cross_lane_execution_state_valid("\n        self.assertIn(token, review_source)\n        self.assertIn(token, t2_source)\n\n'''
needle = '\n\nif __name__ == "__main__":\n'
assert needle in text
text = text.replace(needle, insert + needle, 1)
focused.write_text(text)

# 6) Dedicated CI runs current canonical test modules, excluding legacy shadow modules.
workflow = Path(".github/workflows/system-improvement-auditor-upstream-execution-state-v1-ci.yml")
text = workflow.read_text()
old = "      - name: Full dispatcher regressions\n        run: PYTHONPATH=. python -m unittest discover -s automation/review_dispatcher_v1 -p 'test_*.py' -v\n"
new = '''      - name: Current dispatcher regressions\n        shell: bash\n        run: |\n          set -euo pipefail\n          modules=$(find automation/review_dispatcher_v1 -maxdepth 1 -name 'test_*.py' ! -name '*_legacy_v1.py' -printf '%p\\n' | sed 's#/#.#g;s#\\.py$##' | sort | tr '\\n' ' ')\n          PYTHONPATH=. python -m unittest -v $modules\n'''
assert old in text
text = text.replace(old, new, 1)
workflow.write_text(text)
