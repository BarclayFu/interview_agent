import pytest

from interview_agent.core.storage import ensure_bucket, get_bytes, put_bytes

pytestmark = [pytest.mark.integration]


async def test_roundtrip():
    await ensure_bucket()
    await put_bytes("test/hello.txt", b"hello s3", "text/plain")
    assert await get_bytes("test/hello.txt") == b"hello s3"
