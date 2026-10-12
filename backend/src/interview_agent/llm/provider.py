"""模型接入层 v0（spec §5.5）。

- Provider 协议：stream / structured 两个动作，节点与 worker 只认协议。
- DeepSeekProvider：langchain-openai 的 ChatOpenAI（OpenAI 兼容端点）；
  structured 用 JSON mode + Pydantic 校验 + 失败重试一次。
- StubProvider：确定性桩，零凭据开发/测试/CI 集成测试的默认。
- 路由（M1 硬编码常量）：对话 deepseek-chat；报告 deepseek-reasoner（由调用方构造）。
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol, get_args, get_origin

from pydantic import BaseModel, SecretStr, ValidationError
from pydantic.fields import FieldInfo

from interview_agent.core.config import get_settings
from interview_agent.llm.ledger import Usage, now_ms, record_usage

Message = dict[str, str]  # {"role": "system"|"user"|"assistant", "content": "..."}


class Provider(Protocol):
    def stream(
        self,
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> AsyncIterator[str]: ...

    async def structured(
        self,
        schema: type[BaseModel],
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> Any: ...


class DeepSeekProvider:
    def __init__(self, model: str | None = None) -> None:
        from langchain_openai import ChatOpenAI

        s = get_settings()
        if not s.deepseek_api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY")
        self.model = model or s.llm_model_chat
        self._chat = ChatOpenAI(
            model=self.model,
            base_url=s.deepseek_base_url,
            api_key=SecretStr(s.deepseek_api_key),
            temperature=0.7,
            timeout=30,
            max_retries=2,  # 指数退避由 SDK 实现
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> AsyncIterator[str]:
        start = now_ms()
        prompt_tokens = 0
        completion_tokens = 0
        async for chunk in self._chat.astream(messages):
            text = chunk.content
            if isinstance(text, str) and text:
                yield text
            if chunk.usage_metadata:
                prompt_tokens = int(chunk.usage_metadata.get("input_tokens", 0))
                completion_tokens = int(chunk.usage_metadata.get("output_tokens", 0))
        await record_usage(
            Usage(
                session_id=session_id,
                node=node,
                provider="deepseek",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=int(now_ms() - start),
            )
        )

    async def structured(
        self,
        schema: type[BaseModel],
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> Any:
        chat = self._chat.bind(response_format={"type": "json_object"})
        last_err: Exception | None = None
        for _ in range(2):  # 解析失败重试一次（spec §5.5）
            start = now_ms()
            resp = await chat.ainvoke(messages)
            raw = str(resp.content).strip()
            try:
                data = json.loads(_strip_code_fence(raw))
                out = schema.model_validate(data)
                usage: dict[str, Any] = dict(resp.usage_metadata or {})
                await record_usage(
                    Usage(
                        session_id=session_id,
                        node=node,
                        provider="deepseek",
                        model=self.model,
                        prompt_tokens=int(usage.get("input_tokens", 0)),
                        completion_tokens=int(usage.get("output_tokens", 0)),
                        latency_ms=int(now_ms() - start),
                    )
                )
                return out
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                retry_hint = {
                    "role": "user",
                    "content": f"输出不合法（{e}）。请只输出符合 schema 的 JSON。",
                }
                messages = [
                    *messages,
                    {"role": "assistant", "content": raw},
                    retry_hint,
                ]
        raise RuntimeError(f"结构化输出两次均不合法: {last_err}")


class StubProvider:
    """确定性桩：所有方法不依赖网络，输出可预测。"""

    model = "stub"

    async def stream(
        self,
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> AsyncIterator[str]:
        text = "好的，我们来聊聊你这个项目。先整体介绍一下它的架构和你的职责？"
        async for tok in _tokenize(text):
            yield tok
        await record_usage(Usage(session_id, node, "stub", self.model, 10, 20, 1))

    async def structured(
        self,
        schema: type[BaseModel],
        messages: list[Message],
        *,
        node: str = "unknown",
        session_id: uuid.UUID | str | None = None,
    ) -> Any:
        if schema.__name__ == "ExtractedProjects":
            from interview_agent.reports.extract import ExtractedProject, ExtractedProjects

            await record_usage(Usage(session_id, node, "stub", self.model, 10, 20, 1))
            return ExtractedProjects(
                projects=[
                    ExtractedProject(
                        name="订单系统重构",
                        period="2023.03-2024.01",
                        role="后端负责人",
                        tech=["Python", "PostgreSQL", "Redis"],
                        claims=["峰值 QPS 从 800 提升到 2400"],
                    ),
                    ExtractedProject(
                        name="支付网关", role="核心开发", tech=["Go", "MySQL"], claims=[]
                    ),
                ]
            )
        if schema.__name__ == "DecideResult":
            from interview_agent.reports.decide import DecideResult

            await record_usage(Usage(session_id, node, "stub", self.model, 10, 20, 1))
            return DecideResult(
                score=6,
                rationale="stub-rationale",
                evidence="stub-evidence",
                next_action="next_question",
                reply="stub-reply",
            )
        sample = {name: _synth_value(name, field) for name, field in schema.model_fields.items()}
        await record_usage(Usage(session_id, node, "stub", self.model, 10, 20, 1))
        return schema.model_validate(sample)


_provider: Provider | None = None


def get_provider() -> Provider:
    global _provider
    if _provider is None:
        s = get_settings()
        if s.use_stub_llm or not s.deepseek_api_key:
            _provider = StubProvider()
        else:
            _provider = DeepSeekProvider()
    return _provider


def reset_provider() -> None:
    """测试用：清空单例。"""
    global _provider
    _provider = None


def _strip_code_fence(raw: str) -> str:
    raw = raw.strip("` \n")
    if raw.startswith("json"):
        raw = raw[4:]
    return raw.strip()


def _synth_value(name: str, field: FieldInfo) -> Any:
    """按字段类型合成最小合法值（Stub 专用）。"""
    ann = field.annotation
    if ann is int:
        return 5
    if ann is float:
        return 5.0
    if ann is str:
        return f"stub-{name}"
    if ann is bool:
        return False
    origin = get_origin(ann)
    if origin is Literal:
        args = get_args(ann)
        return args[0] if args else None
    if origin in (list, set, tuple):
        return []
    if origin is dict or ann is dict:
        return {}
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        return {k: _synth_value(k, f) for k, f in ann.model_fields.items()}
    if field.default is not None and field.default.__class__.__name__ != "PydanticUndefinedType":
        return field.default
    return None


async def _tokenize(text: str) -> AsyncIterator[str]:
    """把一句话切成「像 token 一样的片段」（中文按字、英文按词）。"""
    buf = ""
    for ch in text:
        if ch.isascii() and not ch.isspace():
            buf += ch
        else:
            if buf:
                yield buf
                buf = ""
            yield ch
    if buf:
        yield buf
