from dataclasses import dataclass
from config.provider import CapabilityRegistry, ProviderRegistry

@dataclass(frozen=True)
class RoutingRequest:
    task_type: str
    min_quality: float = 0.0
    min_reliability: float = 0.0
    max_usage_cost: float | None = None
    required_tools: tuple[str, ...] = ()
    forbidden_independence_tags: tuple[str, ...] = ()
    require_independent_auditor: bool = False
    allow_external: bool = False

class MissionRouter:
    """Deterministic, fail-closed bridge from capability evidence to an executable adapter."""
    def __init__(self, capabilities: CapabilityRegistry, providers: ProviderRegistry):
        self.capabilities=capabilities
        self.providers=providers

    def select(self, request: RoutingRequest):
        records=self.capabilities.eligible(
            request.task_type,
            min_quality=request.min_quality,
            min_reliability=request.min_reliability,
            max_usage_cost=request.max_usage_cost,
            required_tools=request.required_tools,
            forbidden_independence_tags=request.forbidden_independence_tags,
            require_independent_auditor=request.require_independent_auditor,
        )
        for record in records:
            try:
                provider=self.providers.get_provider(record.provider_id)
            except ValueError:
                continue
            caps=provider.capabilities
            if request.task_type not in caps.capabilities:
                continue
            if caps.external_calls and not request.allow_external:
                continue
            return provider, record
        raise RuntimeError("No eligible executable provider; routing fails closed")
