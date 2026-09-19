import logging
from abc import ABC, abstractmethod

class ProviderInterface(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        raise NotImplementedError

class MockGeminiAdapter(ProviderInterface):
    """Simulation only. No external provider call."""
    def __init__(self):
        self.provider_id="mock_gemini"
        self.health="SIMULATION"

    def generate_response(self, prompt: str) -> str:
        logging.info("[Provider:%s] simulation only", self.provider_id)
        return f"[SIMULATION] claim for: {prompt}"

class ProviderRegistry:
    def __init__(self):
        self.providers={"mock_gemini":MockGeminiAdapter()}

    def get_provider(self, name: str) -> ProviderInterface:
        provider=self.providers.get(name)
        if not provider:
            raise ValueError(f"Unknown provider: {name}")
        return provider
