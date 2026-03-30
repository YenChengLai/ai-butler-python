import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    固定鎖定向 Gemini (text-embedding-004) 索取 Embedding 向量的服務。
    無論主要的 LLMProvider 使用什麼模型（如 Claude），記憶搜尋的向量空間必須保持完全一致。
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EmbeddingService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, model_name: str = "models/text-embedding-004"):
        if hasattr(self, "_initialized"):
            return
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY is not set. Embedding requires Gemini.")
            
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self._initialized = True
        logger.info("✅ EmbeddingService initialized with fixed model: %s", model_name)

    async def get_embedding(self, text: str) -> list[float]:
        """
        非同步取得文字的 768 維 Embedding 向量。
        """
        # Note: google.generativeai SDK's embed_content allows you to call via genai.embed_content_async (or simply wrap via asyncio if not natively async)
        # Based on current google-generativeai==0.8.3, we can use genai.embed_content_async if available, 
        # or just fallback to thread/execution for it. Actually, `client.embed_content_async` is part of genai.
        
        try:
            # Although genai may have _async, let's use the standard embed_content.
            # If genai > 0.4.0, async forms for embedding are usually .embed_content_async
            result = await genai.embed_content_async(
                model=self.model_name,
                content=text,
                task_type="RETRIEVAL_DOCUMENT"
            )
            return result['embedding']
        except AttributeError:
            # Fallback for SDK versions without async embedding
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: genai.embed_content(
                    model=self.model_name, 
                    content=text,
                    task_type="RETRIEVAL_DOCUMENT"
                )
            )
            return result['embedding']
