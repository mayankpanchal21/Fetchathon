import os
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from openai import OpenAI
from ..config import settings

logger = logging.getLogger("agentos.asi1_client")

SUPPORTED_ASI1_MODELS = {
    "asi1": "Default planning and general reasoning model",
    "asi1-mini": "Fast intent classification and low-latency planning model",
    "asi1-ultra": "Advanced reasoning model for complex workflows"
}

OFFICIAL_ASI1_BASE_URL = "https://api.asi1.ai/v1"


class ModelTier(str, Enum):
    DEFAULT = "asi1"
    FAST = "asi1-mini"
    ULTRA = "asi1-ultra"


class ModelConfigError(Exception):
    """Raised when ASI1 API configuration is missing or invalid."""
    pass


class ASI1Client:
    """
    Dedicated client for Fetch.ai's ASI:One model suite (asi1, asi1-mini, asi1-ultra).
    Adheres strictly to the official OpenAI-compatible interface.
    Never connects to unapproved 3rd party LLM providers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or settings.asi1_api_key
        self.base_url = base_url or settings.asi1_base_url or OFFICIAL_ASI1_BASE_URL
        raw_model = (model or settings.asi1_model or "asi1").strip().lower()

        if raw_model not in SUPPORTED_ASI1_MODELS:
            raise ModelConfigError(
                f"Unsupported model '{raw_model}'. AgentOS exclusively uses Fetch.ai ASI:One models: "
                f"{list(SUPPORTED_ASI1_MODELS.keys())}. No third-party LLMs permitted."
            )
        self.default_model = raw_model
        self._client: Optional[OpenAI] = None

        if self.api_key:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=45.0
            )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def route_model(self, task_type: str = "general") -> str:
        """Configurable model router as required by Fetch.ai hackathon specs."""
        if task_type == "intent" or task_type == "fast":
            return ModelTier.FAST.value
        elif task_type == "complex":
            return ModelTier.ULTRA.value
        return self.default_model

    def complete(
        self,
        messages: List[Dict[str, str]],
        model_tier: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        if not self.is_configured:
            raise ModelConfigError(
                "ASI1_API_KEY is not configured. Please set ASI1_API_KEY in .env or environment.\n"
                "To get an API key, register at https://asi1.ai/dashboard/api-keys\n"
                "AgentOS will run in local deterministic demo mode until an ASI1 key is supplied."
            )

        selected_model = model_tier or self.default_model
        if selected_model not in SUPPORTED_ASI1_MODELS:
            raise ModelConfigError(f"Invalid model tier requested: {selected_model}")

        logger.info(f"Querying Fetch.ai ASI1 endpoint [{self.base_url}] using model: {selected_model}")

        kwargs: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Received empty response from ASI:One API.")
            return content.strip()
        except Exception as e:
            logger.error(f"ASI:One API request failed: {e}")
            raise
