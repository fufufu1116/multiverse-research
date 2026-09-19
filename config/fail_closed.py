import sys
import logging
from core_state import CoreStateEngine

class FailClosedEnforcer:
    """
    MULTIVERSE - Fail Closed (安全防壁)
    異常検知時にシステムを安全に停止、または特定機能のみを局所遮断する
    """
    def __init__(self, core: CoreStateEngine):
        self.core = core

    def trigger_system_halt(self, reason: str, details: dict):
        """大域停止: 致命的な不整合時に全システムを安全に強制停止（Kill Switch）"""
        logging.critical(f"【FAIL CLOSED 発動】System Halt: {reason}")
        self.core.log_audit("FAIL_CLOSED_SYSTEM_HALT", {"reason": reason, "details": details})
        
        # OSレベルでの安全なプロセス終了（暴走を物理遮断）
        sys.exit(f"【SYSTEM HALTED】安全防壁が作動しました。理由: {reason}")

    def disable_provider(self, provider_id: str, reason: str):
        """局所停止: 特定のAI（GeminiやClaude等）が応答しない・異常な場合にそのAIだけを切り離す"""
        logging.warning(f"【FAIL CLOSED 局所遮断】Provider [{provider_id}] disabled. Reason: {reason}")
        self.core.disable_provider(provider_id, reason)
        return True
