import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    capabilities: tuple[str, ...]
    mode: str
    external_calls: bool = False

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
