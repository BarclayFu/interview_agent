# M0 · 走路骨架 · 里程碑 Spec

| 字段 | 内容 |
|---|---|
| 状态 | Draft（待评审） |
| 日期 | 2026-09-20 |
| 父设计 | [0001-interview-agent-design.md](./0001-interview-agent-design.md) §5 M0 |
| 估时 | 1 周（每周 30h+） |
| 产出 | 可运行版本 + 演示截图 + 文档更新 |

---

## 1. 目标

打通「浏览器 → CI → 镜像 → k3s → 公网 URL」的完整链路（hello world 级），并备好三层环境与托管服务连接。**不写任何面试业务逻辑。**

一句话验收：打开 Vercel 上的页面，能看到后端版本号，且后端报告 Supabase 与 Upstash 均连通。

## 2. 范围

### 2.1 In Scope

| # | 内容 |
|---|---|
| 1 | 仓库脚手架 + 工具链（uv / ruff / mypy / pytest / pnpm / Makefile / `.gitignore` / `.env.example`） |
| 2 | FastAPI 服务：`/healthz`（存活）、`/readyz`（依赖就绪）、`/version` |
| 3 | Next.js 前端（部署 Vercel）：显示后端版本与连通状态 |
| 4 | 多阶段 Dockerfile（backend） |
| 5 | GitHub Actions：lint + typecheck + test → evals 骨架 → 构建推送 GHCR → 部署 k3s |
| 6 | 3C2G VPS：k3s 安装 + 裁剪配置（严格按父设计 §4.4 的预留/驱逐/GOMEMLIMIT/swap） |
| 7 | Supabase 开通（Postgres + 启用 pgvector）+ Supavisor pooler 连接 |
| 8 | Upstash Redis 开通（TLS 连接） |
| 9 | 本地 kind 全栈骨架（Postgres + Redis + MinIO） |
| 10 | Langfuse Cloud 接通：一条请求产生一条 OTel trace |
| 11 | 密钥管理：本地 `.env`（gitignored）+ 生产 K8s Secret（`kubectl` 手工创建，不进 Git）；Helm 引用 existingSecret |

### 2.2 Out of Scope（M0 不做）

面试业务逻辑 · 任何 LLM 调用 · RAG / 题库 · 评测真实用例 · 监控栈（Prometheus/Grafana）· HPA 清单 · ArgoCD · 简历上传 · 域名与备案最终方案 · 用户界面功能 · 数据库业务表

## 3. 验收标准（DoD）

- [ ] Vercel 页面可访问，显示后端版本号与「DB ✓ / Redis ✓」状态
- [ ] `GET /healthz` 返回 200；`GET /readyz` 在依赖正常时 200、故障时 503 且标注哪个依赖挂了
- [ ] `GET /version` 返回 commit sha 与构建时间
- [ ] 推送 main 后 CI 全绿；镜像进入 GHCR；k3s 完成滚动更新（`kubectl rollout status` 成功）
- [ ] 本地一条命令起开发环境（compose + API + web）；`kind` 全栈可启动
- [ ] Langfuse Cloud 能看到一次请求的 trace
- [ ] 仓库中不存在明文密钥（`.env` 与 K8s Secret 均不入 Git；`.gitignore` 覆盖 `.env` / `.omo/` / `node_modules` / `__pycache__` / `.venv`）
- [ ] `kubectl top` 显示 VPS 上 k3s + API 内存稳定在预算内（整机 < 1.5 GB）

## 4. 仓库结构（锁定）

```
interview_agent/
├─ backend/                     # Python（uv 管理，src 布局）
│  ├─ src/interview_agent/
│  │  ├─ api/                   # FastAPI 路由（M0：healthz / readyz / version）
│  │  ├─ core/                  # 配置、DB/Redis 客户端、OTel 初始化
│  │  └─ __init__.py
│  ├─ tests/
│  ├─ pyproject.toml
│  └─ Dockerfile
├─ web/                         # Next.js（App Router + TS + pnpm）
├─ evals/                       # 评测骨架（M0 仅冒烟断言）
│  ├─ datasets/
│  └─ test_smoke.py
├─ infra/
│  ├─ helm/interview-agent/     # 生产 Helm chart（API/Worker/Ingress/迁移 Job）
│  ├─ kind/kind-config.yaml     # 本地多节点集群配置
│  └─ compose/docker-compose.yml
├─ docs/{specs,adr,plans}/
├─ .github/workflows/{ci.yml,deploy.yml}
├─ .gitignore
├─ .env.example
├─ Makefile
└─ README.md
```

## 5. 接口契约（M0 冻结，后续里程碑沿用）

### 5.1 HTTP

| 端点 | 语义 | 响应 |
|---|---|---|
| `GET /healthz` | 存活探针（liveness） | 200 `{"status":"ok"}` |
| `GET /readyz` | 就绪探针（readiness，接 K8s probe） | 200 `{"db":"ok","redis":"ok"}`；任一故障 → 503 `{"db":"error","redis":"ok"}` |
| `GET /version` | 版本信息 | 200 `{"version":"<git sha>","built_at":"<ISO8601>"}` |

### 5.2 环境变量（配置契约）

| 变量 | 说明 |
|---|---|
| `APP_ENV` | `dev` / `local-full` / `prod` |
| `DATABASE_URL` | Postgres 连接串（prod：Supabase Supavisor pooler，session 模式） |
| `REDIS_URL` | Redis 连接串（prod：`rediss://` Upstash） |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | 观测 |
| `OTEL_SERVICE_NAME` | OTel 服务名 |
| `CORS_ORIGINS` | 允许的前端来源（Vercel 域名） |

约定：本地用 compose 的端点，prod 用托管端点，**应用代码不区分环境**（12-factor）。

### 5.3 端口

API `8000`（容器内 `8000`）；web 本地 `3000`。

## 6. 测试计划

| 层 | 内容 | 触发 |
|---|---|---|
| 单元 | `/healthz`、`/version` 用 FastAPI `TestClient`；`/readyz` 用 stub 依赖注入测 200/503 两态 | 每次 PR |
| 静态 | `ruff check` + `ruff format --check` + `mypy` | 每次 PR |
| 构建 | `docker build` 成功 | 每次 PR |
| 评测骨架 | `evals/test_smoke.py` 跑通（占位断言，验证评测管线可运行） | 每次 PR |
| 集成 | kind 内起服务并 `curl /readyz` | 每次 PR（CI） |
| 手工 | §3 验收清单 + 截图存档 | M0 收尾 |

## 7. 风险与对策（M0 特有）

| 风险 | 对策 |
|---|---|
| k3s 在 2 GB 上 OOM | 严格按父设计 §4.4 配置预留/驱逐/GOMEMLIMIT/swap；安装后先跑 24h 观察 |
| Supabase pooler IPv4-only | 确认 VPS 具备 IPv4；否则改用直连或换 provider |
| 前端（Vercel）与后端跨域 | API 配 `CORS_ORIGINS`；前端用 `NEXT_PUBLIC_API_BASE` |
| 首次 GitHub Actions + GHCR + Vercel 接线繁琐 | 拆成独立小步，每步单独验证（见实现计划） |
| 免费层账号注册与密钥准备 | 列为计划中的前置任务，逐项勾选 |
| 前后端分离 + 无域名 → 混合内容（HTTPS 的 Vercel 页面调 HTTP API 会被浏览器拦截） | M0 内解决：优先 `sslip.io` + cert-manager 给 API 上真 TLS（无需买域名）；若 VPS 在境内导致 80/443 受限，则 M0 暂用 Vercel 服务端代理，M1 前解决 |

## 8. 需用户决策 / 操作（M0 开工前）

| # | 事项 | 状态 / 说明 |
|---|---|---|
| 1 | 仓库与 remote | ✅ 已有：`origin = github.com/BarclayFu/interview_agent`（当前 0 commit）；需首次提交 + 推送 |
| 2 | 账号与密钥 | 用户自行注册并填充环境变量（Supabase / Upstash / Langfuse Cloud / Vercel）；仓库不放密钥 |
| 3 | 无域名 | ✅ 已定：IP 直连，不买域名、不备案 |
| 4 | **VPS 所在地 + TLS** | 待确认境内/境外：境外 → `sslip.io` + cert-manager（真 HTTPS，无需域名）；境内 → 80/443 未备案可能受限，改用 Vercel 服务端代理或另议 |
| 5 | 打包方式 | ✅ Helm（已确认） |
| 6 | 前端形态 | ✅ 前后端分离：`web/` 由 Vercel 部署（Root Directory = `web/`） |
