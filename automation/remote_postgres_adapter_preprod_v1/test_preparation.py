from __future__ import annotations

import unittest

try:
    from .app import (
        ENVIRONMENT_CLASS,
        EXECUTION_AUTHORITY,
        EXPECTED_POSTGRES_ID,
        EXPECTED_RUNTIME_ID,
        RUNTIME,
        TARGET_CLASS,
        RemoteExecutionViolation,
        validate_nonsecret_environment,
    )
    from .validator import validate
except ImportError:
    from app import (
        ENVIRONMENT_CLASS,
        EXECUTION_AUTHORITY,
        EXPECTED_POSTGRES_ID,
        EXPECTED_RUNTIME_ID,
        RUNTIME,
        TARGET_CLASS,
        RemoteExecutionViolation,
        validate_nonsecret_environment,
    )
    from validator import validate


def valid_env():
    return {
        "MULTIVERSE_TARGET_CLASS": TARGET_CLASS,
        "MULTIVERSE_ENVIRONMENT_CLASS": ENVIRONMENT_CLASS,
        "MULTIVERSE_REMOTE_POSTGRES_EXECUTION_AUTHORITY": EXECUTION_AUTHORITY,
        "MULTIVERSE_RUNTIME": RUNTIME,
        "MULTIVERSE_LIVE_BUSINESS_EFFECT": "false",
        "MULTIVERSE_PROTECTED_KEIRIN_DATA": "false",
        "MULTIVERSE_PRODUCTION_CREDENTIALS": "false",
        "MULTIVERSE_INCREMENTAL_SPEND_USD": "0",
        "MULTIVERSE_EXPECTED_POSTGRES_ID": EXPECTED_POSTGRES_ID,
        "MULTIVERSE_RUNTIME_ID": EXPECTED_RUNTIME_ID,
    }


class PreparationTests(unittest.TestCase):
    def assert_code(self, code, fn):
        with self.assertRaises(RemoteExecutionViolation) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)

    def test_valid_nonsecret_gate(self):
        result = validate_nonsecret_environment(valid_env())
        self.assertEqual(result["MULTIVERSE_RUNTIME"], "OFF")

    def test_missing_authority_fails(self):
        env = valid_env()
        del env["MULTIVERSE_REMOTE_POSTGRES_EXECUTION_AUTHORITY"]
        self.assert_code(
            "MISSING_MULTIVERSE_REMOTE_POSTGRES_EXECUTION_AUTHORITY",
            lambda: validate_nonsecret_environment(env),
        )

    def test_runtime_on_fails(self):
        env = valid_env()
        env["MULTIVERSE_RUNTIME"] = "ON"
        self.assert_code(
            "MULTIVERSE_RUNTIME_MISMATCH",
            lambda: validate_nonsecret_environment(env),
        )

    def test_live_effect_true_fails(self):
        env = valid_env()
        env["MULTIVERSE_LIVE_BUSINESS_EFFECT"] = "true"
        self.assert_code(
            "MULTIVERSE_LIVE_BUSINESS_EFFECT_MISMATCH",
            lambda: validate_nonsecret_environment(env),
        )

    def test_protected_keirin_true_fails(self):
        env = valid_env()
        env["MULTIVERSE_PROTECTED_KEIRIN_DATA"] = "true"
        self.assert_code(
            "MULTIVERSE_PROTECTED_KEIRIN_DATA_MISMATCH",
            lambda: validate_nonsecret_environment(env),
        )

    def test_nonzero_spend_fails(self):
        env = valid_env()
        env["MULTIVERSE_INCREMENTAL_SPEND_USD"] = "1"
        self.assert_code(
            "MULTIVERSE_INCREMENTAL_SPEND_USD_MISMATCH",
            lambda: validate_nonsecret_environment(env),
        )

    def test_wrong_postgres_fails(self):
        env = valid_env()
        env["MULTIVERSE_EXPECTED_POSTGRES_ID"] = "wrong"
        self.assert_code(
            "MULTIVERSE_EXPECTED_POSTGRES_ID_MISMATCH",
            lambda: validate_nonsecret_environment(env),
        )

    def test_validator(self):
        result = validate()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["runtime"], "OFF")
        self.assertFalse(result["remote_postgres_execution"])


if __name__ == "__main__":
    unittest.main()
