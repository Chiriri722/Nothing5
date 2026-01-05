from .base import LLMClient
import anthropic
import asyncio
import logging

logger = logging.getLogger(__name__)

class ClaudeClient(LLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model if "claude" in model else "claude-3-haiku-20240307"
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    async def call_async(self, prompt: str, **kwargs) -> str:
        return await asyncio.to_thread(self.call, prompt, **kwargs)
