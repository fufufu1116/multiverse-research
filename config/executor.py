import logging
from core_state import CoreStateEngine
from config.queue import DeterministicTaskQueue
from config.fail_closed import FailClosedEnforcer
from config.provider import ProviderRegistry

class TaskExecutor:
    """Candidate task executor. Provider output is a claim, not verification."""
    def __init__(self, core: CoreStateEngine, queue: DeterministicTaskQueue, fail_closed: FailClosedEnforcer):
        self.core = core
        self.queue = queue
        self.fail_closed = fail_closed
        self.registry = ProviderRegistry()

    def run_next_task(self):
        task = self.queue.fetch_next_task()
        if not task:
            return False
        task_id = task["id"]
        title = task["title"]
        try:
            provider = self.registry.get_provider("mock_gemini")
            result = provider.generate_response(title)
            if not self.core.record_task_claim(task_id, result, provider.provider_id):
                self.queue.mark_task_failed(task_id, "Result claim could not be recorded.")
                return False
            logging.info("Task %s produced an unverified claim.", task_id)
            return True
        except Exception as exc:
            logging.error("Execution error on task %s: %s", task_id, exc)
            self.queue.mark_task_failed(task_id, str(exc))
            return False
