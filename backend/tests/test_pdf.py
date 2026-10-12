import pytest

from interview_agent.core.pdf import InvalidPdfError, ScannedPdfError, extract_text


async def test_extract_text_pdf():
    with open("tests/fixtures/resume_text.pdf", "rb") as f:
        data = f.read()
    text = await extract_text(data)
    assert "张三" in text and "项目" in text


async def test_invalid_pdf_rejected():
    with pytest.raises(InvalidPdfError):
        await extract_text(b"not a pdf at all")


async def test_scanned_pdf_detected():
    import pymupdf

    doc = pymupdf.open()  # 空白 PDF = 无文本层，等价扫描件
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    with pytest.raises(ScannedPdfError):
        await extract_text(data)
