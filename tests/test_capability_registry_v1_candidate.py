import unittest
from config.provider import CapabilityRecord, CapabilityRegistry

class CapabilityRegistryTests(unittest.TestCase):
    def record(self, provider_id, cost, reliability=.9, quality=.9, failures=0, tools=(), tags=()):
        return CapabilityRecord(provider_id,"research",quality,reliability,100,cost,100000,tools,tags,failures,(f"evidence://{provider_id}",))

    def test_least_costly_adequate_provider_is_first(self):
        reg=CapabilityRegistry([self.record("expensive",5),self.record("cheap",1)])
        self.assertEqual([r.provider_id for r in reg.eligible("research",min_quality=.8,min_reliability=.8)],["cheap","expensive"])

    def test_inadequate_or_unevidenced_record_fails(self):
        with self.assertRaises(ValueError):
            CapabilityRegistry([CapabilityRecord("x","research",.9,.9,1,0,100,evidence_refs=())])
        reg=CapabilityRegistry([self.record("weak",0,quality=.2),self.record("good",1)])
        self.assertEqual([r.provider_id for r in reg.eligible("research",min_quality=.8)],["good"])

    def test_independence_and_tool_constraints_filter(self):
        reg=CapabilityRegistry([
            self.record("implementer",0,tools=("github",),tags=("mission_implementer",)),
            self.record("auditor",1,tools=("github",),tags=("independent_auditor",)),
            self.record("offline",0,tools=()),
        ])
        eligible=reg.eligible("research",required_tools=("github",),forbidden_independence_tags=("mission_implementer",))
        self.assertEqual([r.provider_id for r in eligible],["auditor"])

    def test_independent_auditor_requires_canonical_trust_root(self):
        reg=CapabilityRegistry([
            self.record("fake_auditor",0,tags=("independent_auditor",)),
            self.record("auditor_external",1,tags=()),
        ])
        eligible=reg.eligible("research",require_independent_auditor=True)
        self.assertEqual([r.provider_id for r in eligible],["auditor_external"])

    def test_self_declared_independent_tag_grants_no_authority(self):
        reg=CapabilityRegistry([self.record("implementer",0,tags=("independent_auditor",))])
        self.assertEqual(reg.eligible("research",require_independent_auditor=True),[])

    def test_disabled_record_is_not_routable(self):
        r=self.record("disabled",0)
        r=CapabilityRecord(**{**r.__dict__,"enabled":False})
        self.assertEqual(CapabilityRegistry([r]).eligible("research"),[])

if __name__=="__main__":
    unittest.main()
