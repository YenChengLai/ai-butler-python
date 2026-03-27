import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    LLM Provider 抽象基底類別。
    所有 AI 模型（Gemini, Claude 等）都必須實作此介面。
    Agent 只依賴此介面，不感知底層模型。
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        傳入 prompt，回傳純文字 response。
        子類別必須實作此方法。
        """
        pass

    def parse_json_response(self, prompt: str):
        """
        [共用工具] 呼叫 generate() 並自動清洗、解析 JSON。
        統一處理 LLM 常見的 ```json ... ``` 包裝格式。

        回傳: dict 或 list (依 LLM 回傳的 JSON 結構而定)
        拋出: Exception (若解析失敗，由呼叫方處理)
        """
        raw_text = self.generate(prompt)
        # 清洗 LLM 常見的 Markdown code block 包裝
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
