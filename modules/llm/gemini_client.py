from .base import LLMClient
import google.generativeai as genai
import asyncio
import logging

logger = logging.getLogger(__name__)

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        genai.configure(api_key=api_key)
        model_name = model if "gemini" in model else "gemini-pro"
        self.model = genai.GenerativeModel(model_name)
        self.generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )

    def call(self, prompt: str, **kwargs) -> str:
        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text

    async def call_async(self, prompt: str, **kwargs) -> str:
        return await asyncio.to_thread(self.call, prompt, **kwargs)
