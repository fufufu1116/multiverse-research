import logging
from abc import ABC, abstractmethod

class ProviderInterface(ABC):
    """
    MULTIVERSE Provider Interface
    すべてのAI（Gemini, Claude, Local等）はこの規格に従って接続される
    """
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        pass

class MockGeminiAdapter(ProviderInterface):
    """
    Gemini通信用アダプター（モック版：APIキー設定前用の安全なダミー）
    """
    def __init__(self):
        self.provider_id = "gemini_v1"
        self.health = "HEALTHY"

    def generate_response(self, prompt: str) -> str:
        logging.info(f"[Provider: {self.provider_id}] Processing prompt...")
        # 実際にはここにGoogle Gemini APIを叩く処理が入る
        return f"【Gemini Provider】受領しました。指示内容『{prompt}』に対する処理結果です。"

class ProviderRegistry:
    """利用可能なAIプロバイダーを管理・ルーティングする"""
    def __init__(self):
        self.providers = {
            "gemini": MockGeminiAdapter()
        }

    def get_provider(self, name: str) -> ProviderInterface:
        provider = self.providers.get(name)
        if not provider:
            logging.error(f"Provider {name} not found. Fail Closed triggered.")
            raise ValueError(f"Unknown provider: {name}")
        return provider
