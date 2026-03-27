import os
import logging
import google.generativeai as genai

from src.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM Provider。
    包裝 google.generativeai SDK，實作 LLMProvider 介面。
    """

    def __init__(self, model_name: str, generation_config: dict = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY is not set in environment variables.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
        )
        logger.info("✅ GeminiProvider initialized with model: %s", model_name)

    def generate(self, prompt: str) -> str:
        """呼叫 Gemini API，回傳純文字回應。"""
        response = self.model.generate_content(prompt)
        return response.text
