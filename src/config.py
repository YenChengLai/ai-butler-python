import os

# --- Gemini Model Configuration ---
# 統一管理 Model 版本，方便日後升級
GEMINI_MODEL_NAME = "gemini-3-flash-preview"

# (選用) 統一的生成參數，保持回應風格一致
GENERATION_CONFIG = {
    "temperature": 0.7,  # 0.0 ~ 1.0，越低越精確，越高越有創意
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}
