"""
LLM Router — stub for v0.1. LLM_ENABLED=false returns None for all calls.
"""
from typing import Any, Dict, Optional

from app.core.config import settings


class LLMRouter:
    @staticmethod
    def enabled() -> bool:
        return settings.llm_enabled and bool(settings.llm_api_key)

    @staticmethod
    def extract_structured(context: str) -> Optional[Dict[str, Any]]:
        """
        When enabled: call LLM with context, return structured JSON.
        v0.1: always returns None (LLM_ENABLED=false).
        """
        if not LLMRouter.enabled():
            return None
        # TODO v0.2: implement OpenAI-compatible call via settings.llm_base_url
        raise NotImplementedError("LLM extraction not yet implemented")

    @staticmethod
    def summarize(context: str) -> Optional[Dict[str, Any]]:
        if not LLMRouter.enabled():
            return None
        raise NotImplementedError("LLM summarization not yet implemented")


llm_router = LLMRouter()
