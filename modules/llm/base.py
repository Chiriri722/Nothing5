from abc import ABC, abstractmethod
from typing import Optional

class LLMClient(ABC):
    @abstractmethod
    def call(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def call_async(self, prompt: str, **kwargs) -> str:
        pass
