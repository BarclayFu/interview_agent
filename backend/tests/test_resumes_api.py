import pytest
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client():
    return TestClient(create_app())


def test_upload_text_resume_accepted(client):
    r = client.post("/resumes", data={"text": "张三 项目：订单系统 " * 20})
    assert r.status_code == 202
    body = r.json()
    assert body["parse_status"] in ("pending", "parsing", "done")


def test_upload_pdf_resume_accepted(client):
    with open("tests/fixtures/resume_text.pdf", "rb") as f:
        r = client.post("/resumes", files={"file": ("resume.pdf", f, "application/pdf")})
    assert r.status_code == 202


def test_upload_rejects_non_pdf(client):
    r = client.post("/resumes", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_get_resume_status(client):
    rid = client.post("/resumes", data={"text": "李四 项目：网关 " * 20}).json()["resume_id"]
    r = client.get(f"/resumes/{rid}")
    assert r.status_code == 200 and "parse_status" in r.json()
