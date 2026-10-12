"""arq 任务：简历解析（幂等：仅 pending/failed 可重入，先占位再执行）。"""

import uuid
from typing import Any

from sqlalchemy import update

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import Resume
from interview_agent.core.pdf import InvalidPdfError, ScannedPdfError, extract_text
from interview_agent.core.storage import get_bytes
from interview_agent.llm.provider import get_provider
from interview_agent.reports.extract import ExtractedProjects

EXTRACT_PROMPT = """你是简历结构化助手。从以下简历文本中抽取项目清单，只输出 JSON：
{{"projects": [{{"name": str, "period": str, "role": str, "tech": [str],
               "claims": [str]  // 简历中「可追问的声称」，如「QPS 提升3倍」原文
              }}]}}
规则：claims 必须是简历原文片段；抽取不出项目时返回空 projects。
简历文本：
{resume_text}"""


async def parse_resume(ctx: dict[str, Any], resume_id: str) -> None:
    rid = uuid.UUID(resume_id)
    async with get_session_factory()() as s:
        # 幂等占位：仅 pending/failed 能抢到 parsing
        result = await s.execute(
            update(Resume)
            .where(Resume.id == rid, Resume.parse_status.in_(["pending", "failed"]))
            .values(parse_status="parsing")
            .returning(Resume.id)
        )
        if result.scalar_one_or_none() is None:
            return  # 已被处理/处理中：重复消费直接返回
        await s.commit()

        resume = await s.get(Resume, rid)
        if resume is None:
            return
        try:
            if resume.raw_text is None:  # PDF 路径：S3 取件 → 提取文本
                if resume.file_key is None:
                    raise InvalidPdfError("resume 既无文本也无文件")
                resume.raw_text = await extract_text(await get_bytes(resume.file_key))
            out = await get_provider().structured(
                ExtractedProjects,
                [{"role": "user", "content": EXTRACT_PROMPT.format(resume_text=resume.raw_text)}],
                node="parse_resume",
            )
            resume.parsed_projects = [p.model_dump() for p in out.projects]
            resume.parse_status = "done"
            resume.parse_error = None
        except (ScannedPdfError, InvalidPdfError) as e:
            resume.parse_status = "failed"
            resume.parse_error = f"{type(e).__name__}: {e}；可改用粘贴文本入口"
        except Exception as e:  # LLM 失败：标 failed 允许重试入队
            resume.parse_status = "failed"
            resume.parse_error = f"{type(e).__name__}: {e}"
        await s.commit()
