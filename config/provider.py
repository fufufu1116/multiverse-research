import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from core_state import CANONICAL_TRUSTED_VERIFIERS

@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    capabilities: tuple[str, ...]
    mode: str
    external_calls: bool = False

@dataclass(frozen=True)
class CapabilityRecord:
    provider_id: str
    task_type: str
    quality: float
    reliability: float
    latency_ms: int
    usage_cost: float
    context_limit: int
    tool_access: tuple[str, ...] = ()
    independence_tags: tuple[str, ...] = ()  # descriptive only; never grants audit authority
    recent_failures: int = 0
    evidence_refs: tuple[str, ...] = ()
    enabled: bool = True

    def validate(self) -> None:
        if not self.provider_id or not self.task_type: raise ValueError("provider_id/task_type required")
        if not (0.0 <= self.quality <= 1.0): raise ValueError("quality must be 0..1")
        if not (0.0 <= self.reliability <= 1.0): raise ValueError("reliability must be 0..1")
        if self.latency_ms < 0 or self.usage_cost < 0 or self.context_limit < 0 or self.recent_failures < 0:
            raise ValueError("negative capability metric")
        if not self.evidence_refs: raise ValueError("evidence_refs required")

class CapabilityRegistry:
    """Evidence-backed routing metadata. It grants no authority."""
    def __init__(self, records: Iterable[CapabilityRecord] = ()):
        self._records = {}
        for record in records: self.register(record)

    def register(self, record: CapabilityRecord) -> None:
        record.validate()
        self._records[(record.provider_id, record.task_type)] = record

    def eligible(self, task_type: str, *, min_quality: float = 0.0, min_reliability: float = 0.0,
                 max_usage_cost: float | None = None, required_tools: tuple[str, ...] = (),
                 forbidden_independence_tags: tuple[str, ...] = (),
                 require_independent_auditor: bool = False) -> list[CapabilityRecord]:
        out=[]
        for record in self._records.values():
            if not record.enabled or record.task_type != task_type: continue
            if record.quality < min_quality or record.reliability < min_reliability: continue
            if max_usage_cost is not None and record.usage_cost > max_usage_cost: continue
            if any(tool not in record.tool_access for tool in required_tools): continue
            if any(tag in record.independence_tags for tag in forbidden_independence_tags): continue
            # Independent-auditor eligibility is authority-bound, never self-declared metadata.
            if require_independent_auditor and record.provider_id not in CANONICAL_TRUSTED_VERIFIERS: continue
            out.append(record)
        return sorted(out, key=lambda r:(r.usage_cost, r.recent_failures, -r.reliability, -r.quality, r.latency_ms, r.provider_id))

class ProviderInterface(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: raise NotImplementedError
    @abstractmethod
    def generate_response(self, prompt: str) -> str: raise NotImplementedError

class MockGeminiAdapter(ProviderInterface):
    """Simulation only. No external provider call."""
    def __init__(self):
        self.provider_id="mock_gemini"; self.health="SIMULATION"
    @property
    def capabilities(self):
        return ProviderCapabilities(self.provider_id,("text_generation","simulation"),"SIMULATION",False)
    def generate_response(self,prompt):
        logging.info("[Provider:%s] simulation only",self.provider_id)
        return f"[SIMULATION] claim for: {prompt}"

class ProviderRegistry:
    def __init__(self): self.providers={"mock_gemini":MockGeminiAdapter()}
    def get_provider(self,name):
        provider=self.providers.get(name)
        if not provider: raise ValueError(f"Unknown provider: {name}")
        return provider
    def eligible_providers(self,required_capability,allow_external=False):
        return [p for p in self.providers.values()
                if required_capability in p.capabilities.capabilities
                and (allow_external or not p.capabilities.external_calls)]
