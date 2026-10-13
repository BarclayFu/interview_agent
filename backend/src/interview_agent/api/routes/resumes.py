"""简历上传与查询（spec §6.1）。

- 两种入口：multipart PDF（file 字段）或表单纯文本（text 字段，解析失败兜底）。
- PDF 先存 S3 再入队解析；文本直接落库入队（跳过 S3 与 PDF 解析）。
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from interview_agent.core.db import get_db
from interview_agent.core.models import SINGLE_USER_ID, Resume
from interview_agent.core.storage import put_bytes
from interview_agent.worker.enqueue import enqueue_parse_resume

router = APIRouter()
MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post("/resumes", status_code=202)
async def upload_resume(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> dict[str, str]:
    resume = Resume(user_id=SINGLE_USER_ID, parse_status="pending")
    if file is not None:
        data = await file.read()
        if not data.startswith(b"%PDF"):
            raise HTTPException(400, "仅支持 PDF 文件")
        if len(data) > MAX_PDF_BYTES:
            raise HTTPException(400, "PDF 超过 10MB 上限")
        resume.file_key = f"resumes/{resume.id}.pdf"
        await put_bytes(resume.file_key, data, "application/pdf")
    elif text and len(text.strip()) >= 50:
        resume.raw_text = text.strip()
    else:
        raise HTTPException(400, "请上传 PDF 或粘贴不少于 50 字的简历文本")
    db.add(resume)
    await db.commit()
    await enqueue_parse_resume(str(resume.id))
    return {"resume_id": str(resume.id), "parse_status": resume.parse_status}


@router.get("/resumes/{resume_id}")
async def get_resume(
    resume_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "resume not found")
    return {
        "resume_id": str(resume.id),
        "parse_status": resume.parse_status,
        "parsed_projects": resume.parsed_projects,
        "parse_error": resume.parse_error,
        "raw_text_preview": (resume.raw_text or "")[:500],
    }
