# Evals

M1 评测门禁：真实 DeepSeek 调用 + DeepEval。**无 key 时评测整体 skip**，不阻塞本地零凭据开发。

## 运行

```bash
cd backend && uv run pytest ../evals -q        # 全量门禁（约 5-6 分钟，成本 < ¥1）
uv run pytest ../evals -q -k gate1             # 只跑门禁 1（结构化输出，最快）
```

Key 来源（按优先级）：

1. 环境变量 `DEEPSEEK_API_KEY`（CI 由 GitHub Secrets 注入）
2. 本地 `.env` 桥接（应用 Settings，兼容 `DEEPSEEK_API_KEY` 与通用 `API_KEY` 两种命名）

## 四项门禁（spec §5.8）

| 门禁 | 指标 | 阈值 | 用例 |
|---|---|---|---|
| gate1 | 结构化输出合法率（decide + extract schema） | 100% | 8 条 decide 契约 + 3 条抽取（含注入） |
| gate2 | 证据引用率（报告 evidence 可在 transcript 逐字定位） | ≥ 90% | 4 条报告（含低分与注入用例） |
| gate3 | 分数稳定性（同 transcript ×3，各维方差） | ≤ 0.5 | 1 条报告 ×3 次 |
| gate4 | 追问相关性（GEval judge，输入=题目+回答，输出=追问） | ≥ 0.8 | 8 条 decide 中实际触发追问的用例 |

评分不放水与注入防护的断言嵌在 gate1/gate2 的用例期望里（`expect.score_between` / `expect.total_score_max` / `claims_locatable`）。

## 数据集 `datasets/golden_v1/`

十五条 JSON，三种 kind：

- `decide`（8）：面试官判定的契约与评分边界；含诚实度（06）与注入攻击（07/08）
- `extract`（3）：简历抽取；含混乱格式（10）与注入（11，claims 必须原文可定位）
- `report`（4）：报告生成；含极短回答低分约束（14）与 transcript 注入（15）

新增用例规则：给每条写 `note` 说明意图；期望尽量单一（一个用例只验证一个核心行为），避免把「好答案必须换题」这类过程偏好写死——好答案继续深挖（followup）是合法且常见的行为。

## 设计约束

- 评测全程共用一个 session 级事件循环（`runtime.py`）：langchain-openai 的客户端状态与首个 loop 绑定，跨 loop 复用会抛 `Event loop is closed`（用裸 openai SDK 对照验证过：问题在 langchain 层）。生产是单长驻 loop，行为一致。
- judge 走同步 OpenAI 客户端 + `asyncio.to_thread`，天然规避同类问题。
- prompt 变更（`engine/prompts.py` / `worker/tasks.py`）必须重跑本目录门禁并单独提交——评测集就是 prompt 的回归护栏。
