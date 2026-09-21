"""评测骨架：先证明「评测管线可运行」。M1 起替换为真实 golden 用例。"""

import os

import httpx

API_BASE = os.getenv("EVAL_API_BASE", "")


def test_eval_harness_is_wired():
    """冒烟：本目录能被 pytest 收集到。"""
    assert True


def test_readyz_contract_when_api_available():
    """若提供 EVAL_API_BASE，则校验 /readyz 的响应契约。"""
    if not API_BASE:
        return
    r = httpx.get(f"{API_BASE}/readyz", timeout=5)
    assert r.status_code in (200, 503)
    assert set(r.json()) == {"db", "redis"}
