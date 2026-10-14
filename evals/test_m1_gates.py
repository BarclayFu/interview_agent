"""M1 四项评测门禁（spec §5.8）。运行：cd backend && uv run pytest ../evals -q

门禁：
 1) 结构化输出合法率 100%（decide + extract 两类 schema，含注入攻击用例）
 2) 证据引用率 ≥ 90%（报告 evidence 必须能在 transcript 中逐字定位）
 3) 分数稳定性（同 transcript ×3，各维方差 ≤ 0.5）
 4) 追问相关性（GEval judge ≥ 0.8，约 4/5）

真实 DeepSeek 调用：本地从 .env 桥接 key；CI 由 secrets 注入；无 key 整体 skip。
"""

import json
import statistics
import sys
from pathlib import Path
from typing import Any

import pytest

from runtime import run_async

sys.path.insert(0, str(Path(__file__).parent))

DATA = Path(__file__).parent / "datasets" / "golden_v1"


def _norm(s: str) -> str:
    """空白 + 常见标点归一化：定位判断只看内容。"""
    for ch in " \t\r\n。，、；：,.()（）「」":
        s = s.replace(ch, "")
    return s


def _cases(kind: str) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for f in sorted(DATA.glob("*.json")):
        c = json.loads(f.read_text(encoding="utf-8"))
        if c["kind"] == kind:
            out.append((f.stem, c))
    return out


DECIDE_CASES = _cases("decide")
EXTRACT_CASES = _cases("extract")
REPORT_CASES = _cases("report")
DECIDE_IDS = [n for n, _ in DECIDE_CASES]
EXTRACT_IDS = [n for n, _ in EXTRACT_CASES]


def _decide_prompt(case: dict[str, Any]) -> str:
    from interview_agent.engine.prompts import DECIDE_INSTRUCTION

    return f"{DECIDE_INSTRUCTION}\n当前问题：{case['question']}\n候选人回答：{case['answer']}"


def _extract_prompt(case: dict[str, Any]) -> str:
    from interview_agent.worker.tasks import EXTRACT_PROMPT

    return EXTRACT_PROMPT.format(resume_text=case["resume_text"])


def _report_prompt(case: dict[str, Any]) -> str:
    from interview_agent.reports.schema import DIMENSIONS
    from interview_agent.worker.tasks import REPORT_PROMPT

    return REPORT_PROMPT.format(
        dimensions="、".join(DIMENSIONS),
        transcript=case["transcript"],
        scores=case["scores"],
    )


# ============ 门禁 1：结构化输出合法率 100% ============
@pytest.mark.parametrize("name,case", DECIDE_CASES, ids=DECIDE_IDS)
def test_gate1_decide_contract(name: str, case: dict[str, Any]) -> None:
    from interview_agent.llm.provider import DeepSeekProvider
    from interview_agent.reports.decide import DecideResult

    provider = DeepSeekProvider()
    out: DecideResult = run_async(
        provider.structured(
            DecideResult,
            [{"role": "user", "content": _decide_prompt(case)}],
            node=f"gate1:{name}",
        )
    )
    lo, hi = case["expect"]["score_between"]
    assert lo <= out.score <= hi, f"{name}: score={out.score} 超出 [{lo},{hi}]"
    assert out.next_action in case["expect"]["next_action_in"], (
        f"{name}: next_action={out.next_action} 不在 {case['expect']['next_action_in']}"
    )


@pytest.mark.parametrize("name,case", EXTRACT_CASES, ids=EXTRACT_IDS)
def test_gate1_extract_contract(name: str, case: dict[str, Any]) -> None:
    from interview_agent.llm.provider import DeepSeekProvider
    from interview_agent.reports.extract import ExtractedProjects

    provider = DeepSeekProvider()
    out: ExtractedProjects = run_async(
        provider.structured(
            ExtractedProjects,
            [{"role": "user", "content": _extract_prompt(case)}],
            node=f"gate1:{name}",
        )
    )
    assert len(out.projects) >= case["expect"]["min_projects"], (
        f"{name}: 仅抽出 {len(out.projects)} 个项目"
    )
    if case["expect"].get("claims_locatable"):
        text = _norm(case["resume_text"])
        for p in out.projects:
            for claim in p.claims:
                assert _norm(claim) in text, (
                    f"{name}: claim「{claim}」不是简历原文片段（疑被注入影响）"
                )


# ============ 门禁 2：证据引用率 ≥ 90% ============
def test_gate2_evidence_citation_rate() -> None:
    from interview_agent.core.config import get_settings
    from interview_agent.llm.provider import DeepSeekProvider
    from interview_agent.reports.schema import ReportV1

    provider = DeepSeekProvider(model=get_settings().llm_model_report)
    total = located = 0
    for name, case in REPORT_CASES:
        report: ReportV1 = run_async(
            provider.structured(
                ReportV1,
                [{"role": "user", "content": _report_prompt(case)}],
                node=f"gate2:{name}",
            )
        )
        transcript = _norm(case["transcript"])
        for item in [*report.highlights, *report.issues]:
            total += 1
            if item.evidence and _norm(item.evidence) in transcript:
                located += 1
        # 注入用例的总分上限（评分不放水）
        cap = case["expect"].get("total_score_max")
        if cap is not None:
            assert report.total_score <= cap, (
                f"{name}: total_score={report.total_score} 超出上限 {cap}（疑被注入影响）"
            )
    rate = located / max(total, 1)
    assert rate >= 0.9, f"证据引用率 {located}/{total} = {rate:.0%} < 90%"


# ============ 门禁 3：分数稳定性（×3，各维方差 ≤ 0.5）============
def test_gate3_score_stability() -> None:
    from interview_agent.core.config import get_settings
    from interview_agent.llm.provider import DeepSeekProvider
    from interview_agent.reports.schema import DIMENSIONS, ReportV1

    name, case = REPORT_CASES[0]  # 12_report_normal
    provider = DeepSeekProvider(model=get_settings().llm_model_report)
    runs: list[ReportV1] = [
        run_async(
            provider.structured(
                ReportV1,
                [{"role": "user", "content": _report_prompt(case)}],
                node=f"gate3:{name}",
            )
        )
        for _ in range(3)
    ]
    # rubric 依从：三次都必须覆盖六维（防止维度漂移）
    for i, run in enumerate(runs):
        names = {d.name for d in run.dimensions}
        assert names == set(DIMENSIONS), f"第 {i + 1} 次维度集合不符：{sorted(names)}"
    # 按维度名称对齐比较（不依赖顺序）
    by_name = [{d.name: d.score for d in run.dimensions} for run in runs]
    for dim_name in DIMENSIONS:
        scores = [m[dim_name] for m in by_name]
        var = statistics.pvariance(scores)
        assert var <= 0.5, f"维度「{dim_name}」方差 {var} > 0.5（三次：{scores}）"


# ============ 门禁 4：追问相关性（GEval ≥ 0.8）============
@pytest.mark.parametrize("name,case", DECIDE_CASES, ids=DECIDE_IDS)
def test_gate4_followup_relevance(name: str, case: dict[str, Any], judge: Any) -> None:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, SingleTurnParams

    from interview_agent.llm.provider import DeepSeekProvider
    from interview_agent.reports.decide import DecideResult

    provider = DeepSeekProvider()
    out: DecideResult = run_async(
        provider.structured(
            DecideResult,
            [{"role": "user", "content": _decide_prompt(case)}],
            node=f"gate4:{name}",
        )
    )
    if out.next_action != "followup" or not out.reply:
        pytest.skip(f"{name}: 未触发追问，跳过相关性评估")
    metric = GEval(
        name="followup-relevance",
        criteria=(
            "追问（reply）是否明确基于候选人上一回答中的具体内容"
            "（数字、技术名词、断言），而非泛泛提问？"
        ),
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model=judge,
        threshold=0.8,
    )
    tc = LLMTestCase(
        input=f"题目：{case['question']}\n候选人回答：{case['answer']}",
        actual_output=out.reply,
    )
    metric.measure(tc)
    assert metric.score >= 0.8, f"{name}: 追问相关性 {metric.score} < 0.8（{out.reply[:60]}…）"
