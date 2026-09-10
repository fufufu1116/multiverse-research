from __future__ import annotations

import io
import json
import unittest

TEST_MODULES = (
    "research.opportunity_engine_v0.test_multiverse_bridge",
    "research.opportunity_engine_v0.test_multiverse_result_bridge",
    "research.opportunity_engine_v0.test_multiverse_review_ensemble",
    "research.opportunity_engine_v0.test_review_adaptation",
)


def validate_review_cycle() -> dict:
    suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    findings = []
    for test, traceback in list(result.failures) + list(result.errors):
        findings.append(
            {
                "test": str(test),
                "detail": traceback[-2000:],
            }
        )
    return {
        "validator": "MULTIVERSE_OPPORTUNITY_REVIEW_CYCLE_VALIDATOR_v1",
        "verdict": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "findings": findings,
        "runtime": "OFF",
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authority": False,
        "automatic_opportunity_execution": False,
        "note": "Repository-only review-cycle validation; does not invoke providers or grant authority.",
    }


def main() -> None:
    print(json.dumps(validate_review_cycle(), sort_keys=True))


if __name__ == "__main__":
    main()
