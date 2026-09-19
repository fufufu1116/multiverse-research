import logging
from core_state import CoreStateEngine
from config.queue import DeterministicTaskQueue
from config.fail_closed import FailClosedEnforcer
from config.provider import CapabilityRecord, CapabilityRegistry, ProviderRegistry
from config.router import MissionRouter, RoutingRequest

class TaskExecutor:
    """Candidate executor. Routing is evidence-backed; provider output remains an unverified claim."""
    def __init__(self, core: CoreStateEngine, queue: DeterministicTaskQueue, fail_closed: FailClosedEnforcer,
                 capabilities: CapabilityRegistry | None = None, registry: ProviderRegistry | None = None):
        self.core = core
        self.queue = queue
        self.fail_closed = fail_closed
        self.registry = registry or ProviderRegistry()
        self.capabilities = capabilities or CapabilityRegistry([CapabilityRecord(
            provider_id="mock_gemini", task_type="simulation", quality=1.0, reliability=1.0,
            latency_ms=0, usage_cost=0.0, context_limit=0,
            evidence_refs=("builtin://mock_gemini/simulation-adapter",),
        )])
        self.router = MissionRouter(self.capabilities, self.registry)

    def run_next_task(self, request: RoutingRequest | None = None):
        # Backward-compatible safe default: simulation only. It cannot authorize external calls.
        request = request or RoutingRequest("simulation")
        task = self.queue.fetch_next_task()
        if not task:
            return False
        task_id = task["id"]
        title = task["title"]
        try:
            provider, record = self.router.select(request)
            if not self.core.is_provider_enabled(provider.provider_id):
                self.queue.mark_task_failed(task_id, "Provider is disabled by fail-closed control.")
                return False
            result = provider.generate_response(title)
            if not self.core.record_task_claim(task_id, result, provider.provider_id):
                self.queue.mark_task_failed(task_id, "Result claim could not be recorded.")
                return False
            logging.info("Task %s produced an unverified claim via evidence ref(s) %s.",
                         task_id, record.evidence_refs)
            return True
        except Exception as exc:
            logging.error("Execution error on task %s: %s", task_id, exc)
            self.queue.mark_task_failed(task_id, str(exc))
            return False
