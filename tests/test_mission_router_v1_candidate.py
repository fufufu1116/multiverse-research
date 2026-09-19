import unittest
from config.provider import CapabilityRecord, CapabilityRegistry, ProviderRegistry
from config.router import MissionRouter, RoutingRequest

def rec(provider_id="mock_gemini", task_type="simulation", cost=0):
    return CapabilityRecord(provider_id,task_type,.9,.9,1,cost,1000,evidence_refs=("evidence://test",))

class MissionRouterTests(unittest.TestCase):
    def test_selects_evidence_backed_executable_provider(self):
        router=MissionRouter(CapabilityRegistry([rec()]),ProviderRegistry())
        provider, record=router.select(RoutingRequest("simulation",min_quality=.8,min_reliability=.8))
        self.assertEqual(provider.provider_id,"mock_gemini")
        self.assertEqual(record.provider_id,"mock_gemini")

    def test_registry_record_without_adapter_fails_closed(self):
        router=MissionRouter(CapabilityRegistry([rec("ghost")]),ProviderRegistry())
        with self.assertRaises(RuntimeError):
            router.select(RoutingRequest("simulation"))

    def test_adapter_capability_mismatch_fails_closed(self):
        router=MissionRouter(CapabilityRegistry([rec(task_type="research")]),ProviderRegistry())
        with self.assertRaises(RuntimeError):
            router.select(RoutingRequest("research"))

    def test_external_calls_cannot_be_unlocked_by_routing_request(self):
        class External(type(ProviderRegistry().get_provider("mock_gemini"))):
            @property
            def capabilities(self):
                from config.provider import ProviderCapabilities
                return ProviderCapabilities("external",("simulation",),"LIVE",True)
        providers=ProviderRegistry(); providers.providers={"external":External()}; providers.providers["external"].provider_id="external"
        router=MissionRouter(CapabilityRegistry([rec("external")]),providers)
        with self.assertRaises(RuntimeError):
            router.select(RoutingRequest("simulation"))
        self.assertNotIn("allow_external", RoutingRequest.__dataclass_fields__)

if __name__=="__main__":
    unittest.main()
