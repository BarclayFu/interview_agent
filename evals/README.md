# Evals

评测数据集与用例。当前为 M0 骨架（冒烟断言），M1 起接入 DeepEval 的真实指标。

## 运行

    cd backend && uv run pytest ../evals -q

针对运行中的 API 校验契约：

    EVAL_API_BASE=http://localhost:8000 cd backend && uv run pytest ../evals -q
