"""LLM 新闻分析：OpenAI 兼容接口（支持 DeepSeek / NVIDIA / 本地模型）"""

import os
import logging
from typing import Protocol, runtime_checkable

from openai import OpenAI

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    def analyze(self, prompt: str, context: dict) -> str: ...
    def analyze_with_role(self, system_message: str, prompt: str) -> str: ...


class OpenAICompatProvider:
    """OpenAI 兼容 LLM 提供者"""

    def __init__(self):
        # 设置代理环境变量让 httpx 自动走代理
        proxy = os.getenv("LLM_PROXY")
        if proxy:
            os.environ.setdefault("HTTPS_PROXY", proxy)
            os.environ.setdefault("HTTP_PROXY", proxy)
        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_API_BASE", "https://integrate.api.nvidia.com/v1"),
            timeout=60.0,
        )
        self.model = os.getenv("LLM_MODEL", "deepseek-ai/deepseek-v3.2")

    def analyze(self, prompt: str, context: dict) -> str:
        return self.analyze_with_role(
            "你是A股板块轮动分析师，擅长从新闻政策中提取板块影响。回复用中文，简洁专业。",
            prompt,
        )

    def analyze_with_role(self, system_message: str, prompt: str) -> str:
        """带自定义角色的LLM调用"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                timeout=120,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"[LLM调用失败: {e}]"
