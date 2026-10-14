"""评测环境：key 桥接 + 无 key 跳过。

- 本地：从应用 Settings 桥接（兼容 .env 中 DEEPSEEK_API_KEY 或通用 API_KEY 两种命名）
- CI：由 secrets 直接注入 DEEPSEEK_API_KEY
- 无 key：评测整体 skip（本地零凭据不阻塞；M0 冒烟用例不受影响）
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def _bridge_key() -> None:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    try:
        from interview_agent.core.config import get_settings

        key = get_settings().deepseek_api_key
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key
    except Exception:
        pass


_bridge_key()  # 模块导入期执行：必须早于 collection 的 skip 判定


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    skip = pytest.mark.skip(reason="需要 DEEPSEEK_API_KEY（本地 .env / CI secrets）")
    for item in items:
        if "m1_gates" in item.nodeid:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def judge():  # type: ignore[no-untyped-def]
    from deepseek_judge import DeepSeekJudge

    return DeepSeekJudge()
