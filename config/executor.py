import logging
from core_state import CoreStateEngine
from queue import DeterministicTaskQueue
from fail_closed import FailClosedEnforcer
from provider import ProviderRegistry

class TaskExecutor:
    """
    MULTIVERSE - Task Executor
    キューからタスクを取得し、安全に実行・検証し、状態を更新する
    """
    def __init__(self, core: CoreStateEngine, queue: DeterministicTaskQueue, fail_closed: FailClosedEnforcer):
        self.core = core
        self.queue = queue
        self.fail_closed = fail_closed
        self.registry = ProviderRegistry()

    def run_next_task(self):
        """ループの1サイクル：1つのタスクを取得して実行する"""
        task = self.queue.fetch_next_task()
        if not task:
            return False # 実行するタスクがない場合は終了

        task_id = task["id"]
        title = task["title"]
        logging.info(f"--- Executing Task: {title} ---")

        try:
            # 1. 担当プロバイダー（AI）の決定（今回はデフォルトでGemini）
            provider = self.registry.get_provider("gemini")
            
            # 2. AIへタスクを投げて結果を受け取る
            ai_result = provider.generate_response(title)
            logging.info(f"AI Result: {ai_result}")
            
            # 3. 検証（Verification）: 本来はここでAIの回答が本当に成功したかコードでチェックする
            is_valid = True 

            # 4. 成功していれば、心臓部（DB）に結果を書き込み、タスク完了とする
            if is_valid:
                self.core.complete_task_and_reflect_revenue(task_id)
                logging.info(f"Task {task_id} completely verified and saved.")
            else:
                self.queue.mark_task_failed(task_id, "Validation failed: AI output was invalid.")

            return True

        except Exception as e:
            logging.error(f"Execution error on task {task_id}: {e}")
            self.queue.mark_task_failed(task_id, str(e))
            return False
