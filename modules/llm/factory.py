from typing import Optional
import logging
from .base import LLMClient

logger = logging.getLogger(__name__)

def create_llm_client(
    credential_source: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int
) -> Optional[LLMClient]:

    if credential_source == "gemini":
        try:
            from .gemini_client import GeminiClient
            return GeminiClient(api_key, model, temperature, max_tokens)
        except ImportError:
            logger.error("Failed to import GeminiClient. Please ensure google-generativeai is installed.")
            raise

    elif credential_source == "claude":
        try:
            from .claude_client import ClaudeClient
            return ClaudeClient(api_key, model, temperature, max_tokens)
        except ImportError:
            logger.error("Failed to import ClaudeClient. Please ensure anthropic is installed.")
            raise

    else:
        # OpenAI is default and expected to be present
        try:
            from .openai_client import OpenAIClient
            return OpenAIClient(api_key, base_url, model, temperature, max_tokens, timeout)
        except ImportError:
            logger.error("Failed to import OpenAIClient. Please ensure openai is installed.")
            raise
