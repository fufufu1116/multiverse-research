import unittest

from research.opportunity_engine_v0.execution_environment import (
    WorkloadKind,
    route_execution_environment,
)


class ExecutionEnvironmentTests(unittest.TestCase):
    def test_web_app_can_be_phone_cloud_first(self):
        result = route_execution_environment(
            workload=WorkloadKind.WEB_APP,
            owner_has_mac=False,
            cloud_build_available=True,
        )
        self.assertTrue(result["phone_can_complete"])
        self.assertEqual(result["state"], "FEASIBLE_PHONE_ONLY")

    def test_native_ios_can_use_cloud_mac_bridge(self):
        result = route_execution_environment(
            workload=WorkloadKind.NATIVE_IOS_APP,
            owner_has_mac=False,
            cloud_build_available=True,
        )
        self.assertTrue(result["phone_can_complete"])
        self.assertEqual(result["state"], "CLOUD_BRIDGE_AVAILABLE")

    def test_local_xcode_toolchain_requires_mac(self):
        result = route_execution_environment(
            workload=WorkloadKind.NATIVE_IOS_APP,
            owner_has_mac=False,
            cloud_build_available=False,
            local_xcode_required=True,
        )
        self.assertFalse(result["phone_can_complete"])
        self.assertEqual(result["state"], "MAC_REQUIRED_FOR_SELECTED_LOCAL_TOOLCHAIN")

    def test_large_simulation_marks_mac_as_high_leverage(self):
        result = route_execution_environment(
            workload=WorkloadKind.LARGE_SIMULATION,
            owner_has_mac=False,
            cloud_build_available=True,
            local_compute_need=5,
        )
        self.assertEqual(result["mac_leverage_score"], 5)
        self.assertEqual(result["primary_environment"], "PHONE_CONTROLLED_CLOUD_COMPUTE")

    def test_mac_is_preferred_for_local_compute(self):
        result = route_execution_environment(
            workload=WorkloadKind.DATA_PIPELINE,
            owner_has_mac=True,
            cloud_build_available=True,
            local_compute_need=4,
        )
        self.assertEqual(result["state"], "MAC_PREFERRED")
        self.assertEqual(result["primary_environment"], "MAC_LOCAL")


if __name__ == "__main__":
    unittest.main()
