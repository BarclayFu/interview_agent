"""PDF 解析器抽象 + PyMuPDF 默认实现（spec §5.3）。

- 可替换：替换 extract_text 实现即可（如 CLI 包装 marker/docling），ADR 记录选型。
- 仅支持文字型 PDF：提取字符数 < MIN_CHARS 判为扫描件，抛 ScannedPdfError（OCR 不做）。
"""

import asyncio

MIN_CHARS = 100


class ScannedPdfError(Exception):
    """扫描件/图片型 PDF：无法提取文本。"""


class InvalidPdfError(Exception):
    """非 PDF 或文件损坏。"""


def _extract(data: bytes) -> str:
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as e:
        raise InvalidPdfError(str(e)) from e
    try:
        text = "\n".join(
            doc.load_page(i).get_text()  # type: ignore[no-untyped-call]
            for i in range(doc.page_count)
        ).strip()
    finally:
        doc.close()  # type: ignore[no-untyped-call]
    if len(text) < MIN_CHARS:
        raise ScannedPdfError(f"提取字符数 {len(text)} < {MIN_CHARS}，疑似扫描件")
    return text


async def extract_text(data: bytes) -> str:
    return await asyncio.to_thread(_extract, data)
