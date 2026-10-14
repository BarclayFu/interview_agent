"""DeepEval 自定义 judge 模型：把 DeepEval 的 LLM 调用指向 DeepSeek（OpenAI 兼容）。

支持两种调用形态：
- generate(prompt) -> str
- generate(prompt, schema) -> schema 实例（JSON mode + Pydantic 校验）
"""

import asyncio
import json
import os
from typing import Any

from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import BaseModel


class DeepSeekJudge(DeepEvalBaseLLM):
    def __init__(self, model: str = "deepseek-chat") -> None:
        from openai import OpenAI

        self._model_name = model
        self._client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )

    def load_model(self) -> Any:
        return self._client

    def get_model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
        content = prompt
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
        }
        if schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["messages"][0]["content"] += (
                "\n\n请严格按以下 JSON schema 输出（只输出 JSON）：\n"
                + json.dumps(schema.model_json_schema(), ensure_ascii=False)
            )
        resp = self._client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        if schema is not None:
            return schema.model_validate_json(text)
        return text

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
        return await asyncio.to_thread(self.generate, prompt, schema)
