# M0 · 走路骨架 · 实现计划

> **给执行者（agentic workers）：** REQUIRED SUB-SKILL: 使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务执行本计划。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 打通「浏览器 → CI → 镜像 → k3s → 公网 URL」全链路（hello world 级），并备好三层环境与托管服务连接。

**Architecture:** 后端 FastAPI（uv + src 布局）经 Helm 部署到 3C2G VPS 的 k3s，由 Traefik Ingress + sslip.io TLS 暴露；数据外推 Supabase（Postgres + pgvector）与 Upstash（Redis）；前端 Next.js 部署到 Vercel；观测走 OTel → Langfuse Cloud；本地用 docker compose 跑依赖、kind 跑全栈。

**Tech Stack:** Python 3.12 / uv / FastAPI / ruff / mypy / pytest；Next.js（App Router + TS + pnpm）；Docker；GitHub Actions + GHCR；k3s + Helm + Traefik + cert-manager；Supabase / Upstash / Vercel / Langfuse Cloud。

**Spec:** [docs/specs/0002-m0-walking-skeleton.md](../specs/0002-m0-walking-skeleton.md)

**执行说明:** 仓库此前 0 commit，直接在 `main` 上执行（无法开 worktree）。每个 Task 结束提交一次。

---

## 文件结构（职责锁定）

| 路径 | 职责 |
|---|---|
| `backend/pyproject.toml` | Python 依赖与工具配置 |
| `backend/src/interview_agent/core/config.py` | 环境变量配置（pydantic-settings） |
| `backend/src/interview_agent/core/clients.py` | Postgres / Redis 连通性探测 |
| `backend/src/interview_agent/core/telemetry.py` | OTel 初始化（导出 Langfuse Cloud） |
| `backend/src/interview_agent/api/app.py` | FastAPI 装配（路由、CORS） |
| `backend/src/interview_agent/api/routes/health.py` | `/healthz` `/readyz` `/version` |
| `backend/Dockerfile` | 多阶段构建（非 root 运行） |
| `backend/tests/` | pytest 用例 |
| `web/` | Next.js 前端（版本 + 连通状态展示） |
| `evals/test_smoke.py` | 评测骨架（冒烟断言） |
| `infra/compose/docker-compose.yml` | 本地 PG + Redis + MinIO |
| `infra/helm/interview-agent/` | 生产 Helm chart |
| `infra/kind/kind-config.yaml` | 本地多节点集群配置 |
| `.github/workflows/ci.yml` | lint / typecheck / test / build |
| `.github/workflows/deploy.yml` | GHCR 推送 + Helm 部署 |
| `Makefile` | 命令入口 |

---

## Task 1: 仓库脚手架与工具链

**Files:**
- Create: `backend/pyproject.toml`, `backend/src/interview_agent/__init__.py`, `backend/src/interview_agent/api/__init__.py`, `backend/src/interview_agent/core/__init__.py`, `backend/tests/__init__.py`, `.env.example`, `Makefile`

- [ ] **Step 1: 写 `backend/pyproject.toml`**

```toml
[project]
name = "interview-agent"
version = "0.0.1"
description = "AI mock interviewer — backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic-settings>=2.6",
    "asyncpg>=0.30",
    "redis>=5.2",
    "opentelemetry-sdk>=1.29",
    "opentelemetry-exporter-otlp-proto-http>=1.29",
    "opentelemetry-instrumentation-fastapi>=0.50b0",
    "langfuse>=3.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.8",
    "mypy>=1.13",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/interview_agent"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 建包结构并安装依赖**

```bash
mkdir -p backend/src/interview_agent/api/routes backend/src/interview_agent/core backend/tests
touch backend/src/interview_agent/__init__.py \
      backend/src/interview_agent/api/__init__.py \
      backend/src/interview_agent/api/routes/__init__.py \
      backend/src/interview_agent/core/__init__.py \
      backend/tests/__init__.py
cd backend && uv sync --dev
```

Expected: 生成 `backend/uv.lock` 与 `.venv`，退出码 0。

- [ ] **Step 3: 写 `.env.example`**

```bash
# 应用
APP_ENV=dev
CORS_ORIGINS=http://localhost:3000

# 数据层（本地默认值；prod 用托管端点）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/interview_agent
REDIS_URL=redis://localhost:6379/0

# 观测（留空则不导出）
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=https://cloud.langfuse.com
OTEL_SERVICE_NAME=interview-agent-api
```

- [ ] **Step 4: 写 `Makefile`**（配方行必须是 Tab 缩进）

```make
.PHONY: help api web test lint fmt typecheck up down kind-up kind-down

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | cut -d: -f1 | sort

api:
	cd backend && uv run uvicorn interview_agent.api.app:app --reload --port 8000

web:
	cd web && pnpm dev

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .

fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .

typecheck:
	cd backend && uv run mypy src

up:
	docker compose -f infra/compose/docker-compose.yml up -d

down:
	docker compose -f infra/compose/docker-compose.yml down

kind-up:
	kind create cluster --config infra/kind/kind-config.yaml --name interview-agent

kind-down:
	kind delete cluster --name interview-agent
```

- [ ] **Step 5: 提交**

```bash
git add backend .env.example Makefile
git commit -m "chore(backend): 脚手架与工具链（uv/ruff/mypy/pytest + Makefile）"
```

---

## Task 2: 配置层（环境变量契约）

**Files:**
- Create: `backend/src/interview_agent/core/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 写失败测试 `backend/tests/test_config.py`**

```python
from interview_agent.core.config import Settings


def test_cors_origins_parsed_into_list():
    s = Settings(cors_origins="http://localhost:3000, https://foo.vercel.app")
    assert s.cors_origin_list == ["http://localhost:3000", "https://foo.vercel.app"]


def test_defaults_are_local():
    s = Settings()
    assert s.app_env == "dev"
    assert s.database_url.startswith("postgresql://")
    assert s.redis_url.startswith("redis://")
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'interview_agent.core.config'`

- [ ] **Step 3: 实现 `backend/src/interview_agent/core/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/interview_agent"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    otel_service_name: str = "interview-agent-api"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/test_config.py -q`
Expected: `2 passed`

- [ ] **Step 5: 提交**

```bash
git add backend/src/interview_agent/core/config.py backend/tests/test_config.py
git commit -m "feat(backend): 配置层与 CORS 解析"
```

---

## Task 3: `/healthz` 与 `/version`（TDD）

**Files:**
- Create: `backend/src/interview_agent/api/app.py`, `backend/src/interview_agent/api/routes/health.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: 写失败测试 `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app

client = TestClient(create_app())


def test_healthz_returns_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_returns_sha_and_built_at():
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"version", "built_at"}
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/test_health.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'interview_agent.api.app'`

- [ ] **Step 3: 实现 `health.py` 与 `app.py`**

`backend/src/interview_agent/api/routes/health.py`：

```python
import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """存活探针：进程活着就返回 200。"""
    return {"status": "ok"}


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "version": os.getenv("GIT_SHA", "dev"),
        "built_at": os.getenv("BUILT_AT", datetime.now(timezone.utc).isoformat()),
    }
```

`backend/src/interview_agent/api/app.py`：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interview_agent.api.routes import health
from interview_agent.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="interview-agent", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/test_health.py -q`
Expected: `2 passed`

- [ ] **Step 5: 提交**

```bash
git add backend/src/interview_agent/api backend/tests/test_health.py
git commit -m "feat(backend): /healthz 与 /version 端点"
```

---

## Task 4: `/readyz` 依赖就绪探测（TDD）

**Files:**
- Create: `backend/src/interview_agent/core/clients.py`
- Modify: `backend/src/interview_agent/api/routes/health.py`（改为最终版）
- Test: `backend/tests/test_readyz.py`

- [ ] **Step 1: 写失败测试 `backend/tests/test_readyz.py`**

```python
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app
from interview_agent.api.routes import health

client = TestClient(create_app())


async def _ok(_settings) -> None:
    return None


async def _fail(_settings) -> None:
    raise RuntimeError("boom")


def test_readyz_ok(monkeypatch):
    monkeypatch.setattr(health, "check_postgres", _ok)
    monkeypatch.setattr(health, "check_redis", _ok)
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"db": "ok", "redis": "ok"}


def test_readyz_marks_db_error_and_returns_503(monkeypatch):
    monkeypatch.setattr(health, "check_postgres", _fail)
    monkeypatch.setattr(health, "check_redis", _ok)
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"db": "error", "redis": "ok"}
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/test_readyz.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'check_postgres'`

- [ ] **Step 3: 实现 `backend/src/interview_agent/core/clients.py`**

```python
import asyncpg
from redis.asyncio import Redis

from interview_agent.core.config import Settings


def normalize_pg_dsn(url: str) -> str:
    """asyncpg 只认 postgresql:// / postgres://，不认 SQLAlchemy 的 +asyncpg 后缀。"""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def check_postgres(settings: Settings) -> None:
    conn = await asyncpg.connect(dsn=normalize_pg_dsn(settings.database_url), timeout=3)
    try:
        await conn.fetchval("SELECT 1")
    finally:
        await conn.close()


async def check_redis(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url, socket_timeout=3)
    try:
        await client.ping()
    finally:
        await client.aclose()
```

- [ ] **Step 4: 把 `health.py` 替换为最终版**

```python
import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from interview_agent.core.clients import check_postgres, check_redis
from interview_agent.core.config import Settings, get_settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """存活探针：进程活着就返回 200。"""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, str]:
    """就绪探针：任一依赖不可用即 503（接 K8s readinessProbe）。"""
    settings = get_settings()

    async def probe(fn: Callable[[Settings], Awaitable[None]]) -> str:
        try:
            await fn(settings)
            return "ok"
        except Exception:
            return "error"

    db, redis = await asyncio.gather(probe(check_postgres), probe(check_redis))
    result = {"db": db, "redis": redis}
    if "error" in result.values():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "version": os.getenv("GIT_SHA", "dev"),
        "built_at": os.getenv("BUILT_AT", datetime.now(timezone.utc).isoformat()),
    }
```

- [ ] **Step 5: 跑全部检查并提交**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run mypy src`
Expected: 测试全过；ruff 与 mypy 无报错

```bash
git add backend/src/interview_agent/core/clients.py backend/src/interview_agent/api/routes/health.py backend/tests/test_readyz.py
git commit -m "feat(backend): /readyz 依赖就绪探测（Postgres + Redis）"
```

---

## Task 5: 多阶段 Dockerfile

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`

- [ ] **Step 1: 写 `backend/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev

FROM base AS runtime
ARG GIT_SHA=dev
ARG BUILT_AT=unknown
ENV GIT_SHA=${GIT_SHA} BUILT_AT=${BUILT_AT} PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uvicorn", "interview_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 写 `backend/.dockerignore`**

```
.venv
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
tests
```

- [ ] **Step 3: 构建镜像（构建上下文 = 仓库根目录）**

Run:
```bash
docker build -f backend/Dockerfile -t interview-agent-api:dev --build-arg GIT_SHA=$(git rev-parse --short HEAD) .
```
Expected: 构建成功；`docker images` 出现 `interview-agent-api:dev`

- [ ] **Step 4: 起容器验证三个端点**

Run:
```bash
docker run --rm -d --name ia-api -p 8000:8000 interview-agent-api:dev
sleep 2
curl -s localhost:8000/healthz; echo
curl -s localhost:8000/version; echo
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/readyz
docker stop ia-api
```
Expected: `/healthz` → `{"status":"ok"}`；`/version` 含 commit sha；`/readyz` → `503`（本地无 PG/Redis，属预期）

- [ ] **Step 5: 提交**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "build(backend): 多阶段 Dockerfile（非 root + 健康检查）"
```

---

## Task 6: 本地依赖环境（docker compose）

**Files:**
- Create: `infra/compose/docker-compose.yml`

- [ ] **Step 1: 写 `infra/compose/docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: interview_agent
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d interview_agent"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  miniodata:
```

说明：`pgvector/pgvector:pg16` 自带 pgvector 扩展，M1 直接用；MinIO 为简历文件与报告归档预留。

- [ ] **Step 2: 起依赖并等健康**

Run:
```bash
cp .env.example .env
make up
docker compose -f infra/compose/docker-compose.yml ps
```
Expected: 三个服务状态为 `healthy`（或 `running`）

- [ ] **Step 3: 让 `/readyz` 真实连通**

在终端 A：`make api`
在终端 B：
```bash
curl -s localhost:8000/readyz; echo
```
Expected: `{"db":"ok","redis":"ok"}`

- [ ] **Step 4: 收尾清理**

Run: `make down`
Expected: 容器停止（数据卷保留）

- [ ] **Step 5: 提交**

```bash
git add infra/compose/docker-compose.yml
git commit -m "chore(infra): 本地依赖 compose（PG+pgvector / Redis / MinIO）"
```

---

## Task 7: 遥测接入（Langfuse SDK v4）

**Files:**
- Create: `backend/src/interview_agent/core/telemetry.py`
- Modify: `backend/src/interview_agent/api/app.py`（lifespan）、`backend/src/interview_agent/api/routes/health.py`（给 `/version` 加 trace）
- Test: `backend/tests/test_telemetry.py`

背景（调研核实）：Langfuse Python SDK **v4** 是 OTel 原生的，推荐直接用 SDK（而非裸 OTLP）。环境变量为 `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL`；未配置密钥时应优雅降级（本地开发不导出）。

- [ ] **Step 1: 写失败测试 `backend/tests/test_telemetry.py`**

```python
from interview_agent.core.config import Settings
from interview_agent.core.telemetry import init_telemetry


def test_returns_none_when_keys_missing():
    settings = Settings(langfuse_public_key=None, langfuse_secret_key=None)
    assert init_telemetry(settings) is None


def test_returns_client_when_keys_present():
    settings = Settings(langfuse_public_key="pk-lf-test", langfuse_secret_key="sk-lf-test")
    client = init_telemetry(settings)
    assert client is not None
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/test_telemetry.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'interview_agent.core.telemetry'`

- [ ] **Step 3: 实现 `backend/src/interview_agent/core/telemetry.py`**

```python
from langfuse import Langfuse

from interview_agent.core.config import Settings


def init_telemetry(settings: Settings) -> Langfuse | None:
    """初始化 Langfuse（v4，OTel 原生）。未配置密钥时返回 None，本地开发不导出。"""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )
```

- [ ] **Step 4: 接进应用生命周期，并给 `/version` 加 trace**

`app.py` 改为：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interview_agent.api.routes import health
from interview_agent.core.config import get_settings
from interview_agent.core.telemetry import init_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.langfuse = init_telemetry(get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="interview-agent", version="0.0.1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

`health.py` 里给 `/version` 加装饰器（其余不变）：

```python
from langfuse import observe


@router.get("/version")
@observe()
async def version() -> dict[str, str]:
    return {
        "version": os.getenv("GIT_SHA", "dev"),
        "built_at": os.getenv("BUILT_AT", datetime.now(timezone.utc).isoformat()),
    }
```

- [ ] **Step 5: 跑测试 + 真实验证**

Run: `cd backend && uv run pytest -q`
Expected: 全过

真实链路验证（需要用户已在 `.env` 填好 Langfuse 密钥）：
```bash
make api
curl -s localhost:8000/version; echo
```
然后打开 Langfuse Cloud → Traces，应看到一条名为 `version` 的 trace。若密钥为空则不会有 trace，属预期。

- [ ] **Step 6: 提交**

```bash
git add backend/src/interview_agent/core/telemetry.py backend/src/interview_agent/api backend/tests/test_telemetry.py
git commit -m "feat(backend): Langfuse v4 遥测接入（OTel 原生，无密钥优雅降级）"
```

---

## Task 8: Next.js 前端（版本 + 连通状态）

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/next.config.ts`, `web/app/layout.tsx`, `web/app/page.tsx`, `web/app/api-ping.tsx`, `web/.env.example`

- [ ] **Step 1: 写 `web/package.json`**

```json
{
  "name": "interview-agent-web",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 2: 写 `web/tsconfig.json` 与 `web/next.config.ts`**

`web/tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

`web/next.config.ts`：

```ts
import type { NextConfig } from "next";

// 同源代理（BFF）：浏览器只与 Vercel 通信（HTTPS、同源），由 Vercel 服务端转发到 API。
// 因此 API 无需域名与 TLS，也没有混合内容与 CORS 问题。
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/:path*` }];
  },
};

export default nextConfig;
```

- [ ] **Step 3: 写页面（服务端渲染 + 浏览器端探测各一条路径）**

`web/app/layout.tsx`：

```tsx
export const metadata = { title: "Interview Agent" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
```

`web/app/api-ping.tsx`（客户端组件：验证**浏览器 → API** 这条路，即 CORS + TLS）：

```tsx
"use client";

import { useEffect, useState } from "react";

// 走同源代理（/api/* → API_ORIGIN），因此没有 CORS 与混合内容问题
const API_BASE = "/api";

export function ApiPing() {
  const [state, setState] = useState("探测中…");

  useEffect(() => {
    fetch(`${API_BASE}/version`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setState(`浏览器直连成功（version=${d.version}）`))
      .catch((e) => setState(`浏览器直连失败：${e.message}`));
  }, []);

  return <p style={{ color: "#666" }}>{state}</p>;
}
```

`web/app/page.tsx`：

```tsx
import { ApiPing } from "./api-ping";

export const dynamic = "force-dynamic";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_ORIGIN}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function Home() {
  const version = await getJson<{ version: string; built_at: string }>("/version");
  const ready = await getJson<{ db: string; redis: string }>("/readyz");

  return (
    <main style={{ fontFamily: "system-ui", padding: 40, lineHeight: 1.8 }}>
      <h1>Interview Agent · 走路骨架</h1>
      <p>后端版本（服务端渲染）：{version ? version.version : "不可达"}</p>
      <p>DB：{ready?.db ?? "?"} · Redis：{ready?.redis ?? "?"}</p>
      <ApiPing />
      <p style={{ color: "#999", fontSize: 12 }}>API: {API_ORIGIN}</p>
    </main>
  );
}
```

- [ ] **Step 4: 写 `web/.env.example` 并本地验证**

```bash
# 服务端渲染与 /api/* 代理的目标（Vercel 上配置为 http://<VPS_IP>:8000）
API_ORIGIN=http://localhost:8000
```

Run:
```bash
cd web && pnpm install && pnpm run build
```
Expected: 构建成功（页面为 `force-dynamic`，构建期不需要 API 在线）

再本地跑通：
```bash
pnpm dev   # 另开终端，且 make api 已在跑
```
Expected: `http://localhost:3000` 显示后端版本、DB/Redis 状态，且「浏览器直连成功」（经同源代理 `/api/*` 转发）

- [ ] **Step 5: 提交**

```bash
git add web
git commit -m "feat(web): Next.js 骨架（版本 + 依赖状态 + 浏览器直连探测）"
```

---

## Task 9: 评测骨架

**Files:**
- Create: `evals/test_smoke.py`, `evals/README.md`

- [ ] **Step 1: 写 `evals/test_smoke.py`**

```python
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
```

- [ ] **Step 2: 写 `evals/README.md`**

```markdown
# Evals

评测数据集与用例。当前为 M0 骨架（冒烟断言），M1 起接入 DeepEval 的真实指标。

## 运行

    cd backend && uv run pytest ../evals -q

针对运行中的 API 校验契约：

    EVAL_API_BASE=https://<api-host> cd backend && uv run pytest ../evals -q
```

- [ ] **Step 3: 运行验证**

Run: `cd backend && uv run pytest ../evals -q`
Expected: `2 passed`

- [ ] **Step 4: 提交**

```bash
git add evals
git commit -m "test(evals): 评测管线骨架（冒烟 + 契约校验）"
```

---

## Task 10: CI 流水线（GitHub Actions）

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: 写 `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install deps
        working-directory: backend
        run: uv sync --dev
      - name: Lint
        working-directory: backend
        run: uv run ruff check . && uv run ruff format --check .
      - name: Typecheck
        working-directory: backend
        run: uv run mypy src
      - name: Unit tests
        working-directory: backend
        run: uv run pytest -q
      - name: Eval harness
        working-directory: backend
        run: uv run pytest ../evals -q
      - name: Docker build
        run: docker build -f backend/Dockerfile -t interview-agent-api:ci .

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: web/pnpm-lock.yaml
      - name: Install
        working-directory: web
        run: pnpm install --frozen-lockfile
      - name: Build
        working-directory: web
        run: pnpm run build
```

- [ ] **Step 2: 本地模拟关键步骤（可选但推荐）**

Run:
```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q && uv run pytest ../evals -q
cd ../web && pnpm install --frozen-lockfile && pnpm run build
```
Expected: 全部通过（提前排掉 CI 会红的问题）

- [ ] **Step 3: 推送并在 GitHub 上确认 CI 绿**

Run:
```bash
git add .github/workflows/ci.yml
git commit -m "ci: 后端 lint/typecheck/test/eval/docker + 前端 build"
git push
```
Expected: GitHub Actions 页面 `ci` 工作流两个 job 均绿

- [ ] **Step 4: 加 CI badge 到 README**

创建 `README.md`：

```markdown
# Interview Agent

面向中文技术面试的 AI 模拟面试官（作品集项目，SDD 开发）。

![ci](https://github.com/BarclayFu/interview_agent/actions/workflows/ci.yml/badge.svg)

- 设计文档：`docs/specs/0001-interview-agent-design.md`
- M0 里程碑：`docs/specs/0002-m0-walking-skeleton.md`
```

- [ ] **Step 5: 提交**

```bash
git add README.md
git commit -m "docs: 加 README 与 CI badge"
```

---

## Task 11: k3s 安装与 2GB 裁剪（VPS）

**Files:**
- Create: `infra/k3s/config.yaml`（配置进仓库，保证可复现）

前置：确认 VPS 有 IPv4、可 SSH、有 sudo。

- [ ] **Step 1: 写 `infra/k3s/config.yaml`**

```yaml
# k3s 服务端配置（3C2G VPS，按设计文档 §4.4 裁剪）
write-kubeconfig-mode: "0644"

# 生产无集群内状态化负载 → 关掉本地存储供给器，省约 20MB
disable:
  - local-storage

kubelet-arg:
  # 预留：给 OS 与 k3s 自身
  - "system-reserved=cpu=200m,memory=300Mi"
  - "kube-reserved=cpu=200m,memory=600Mi"
  # 驱逐阈值：不设 memory.available 时，内核 OOM killer 可能直接杀掉 k3s-server
  - "eviction-hard=memory.available<100Mi,nodefs.available<10%"
  - "max-pods=50"
  # swap：需显式允许；启用后 LimitedSwap 即为默认行为
  - "fail-swap-on=false"
  - "feature-gates=NodeSwap=true"
```

- [ ] **Step 2: 在 VPS 上准备 swap**

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```
Expected: Swap 行出现 2.0Gi

- [ ] **Step 3: 放入 k3s 配置并安装**

```bash
# 本地 → VPS
scp infra/k3s/config.yaml <user>@<VPS_IP>:/tmp/k3s-config.yaml

# VPS 上
sudo mkdir -p /etc/rancher/k3s
sudo mv /tmp/k3s-config.yaml /etc/rancher/k3s/config.yaml
curl -sfL https://get.k3s.io | sh -
```
Expected: 安装脚本结束且无报错

- [ ] **Step 4: 加 GOMEMLIMIT 并重启**

```bash
sudo mkdir -p /etc/systemd/system/k3s.service.d
sudo tee /etc/systemd/system/k3s.service.d/gomemlimit.conf >/dev/null <<'EOF'
[Service]
Environment="GOMEMLIMIT=800MiB"
EOF
sudo systemctl daemon-reload
sudo systemctl restart k3s
```
Expected: 无报错（GOMEMLIMIT 让 k3s 空闲内存从约 1.2GB 降到约 750MB）

- [ ] **Step 5: 验证集群与资源**

```bash
sudo k3s kubectl get nodes -o wide
free -h
sudo systemctl is-active k3s
```
Expected: 节点 `Ready`；`systemctl is-active` 输出 `active`；内存 used 明显低于 1.5G

- [ ] **Step 6: 导出 kubeconfig（给 CI 用）**

```bash
sudo cat /etc/rancher/k3s/k3s.yaml | sed "s/127.0.0.1/<VPS_IP>/" | base64 -w0; echo
```
Expected: 得到一段 base64 → 保存到 GitHub 仓库 Secret `KUBE_CONFIG`（Task 13 会用）

- [ ] **Step 7: 提交**

```bash
git add infra/k3s/config.yaml
git commit -m "chore(infra): k3s 2GB 裁剪配置（预留/驱逐/GOMEMLIMIT/swap）"
```

---

## Task 12: Helm Chart

**Files:**
- Create: `infra/helm/interview-agent/Chart.yaml`, `values.yaml`, `templates/_helpers.tpl`, `templates/deployment.yaml`, `templates/service.yaml`, `templates/ingress.yaml`, `templates/migration-job.yaml`

- [ ] **Step 1: 写 `Chart.yaml` 与 `values.yaml`**

`infra/helm/interview-agent/Chart.yaml`：

```yaml
apiVersion: v2
name: interview-agent
description: Interview Agent API (M0 walking skeleton)
type: application
version: 0.1.0
appVersion: "0.0.1"
```

`infra/helm/interview-agent/values.yaml`：

```yaml
image:
  repository: ghcr.io/barclayfu/interview-agent-api
  tag: ""                # 部署时 --set image.tag=<sha>
  pullPolicy: IfNotPresent

replicaCount: 1

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 500Mi

# 人工创建的 Secret（不入 Git），键即环境变量名
existingSecret: interview-agent-secrets

ingress:
  enabled: true
  className: traefik
  annotations: {}

migration:
  enabled: false         # M0 无业务表；M1 接 alembic 后打开
```

- [ ] **Step 2: 写 `templates/_helpers.tpl`**

```
{{- define "interview-agent.fullname" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "interview-agent.labels" -}}
app.kubernetes.io/name: {{ include "interview-agent.fullname" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "interview-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "interview-agent.fullname" . }}
{{- end -}}
```

- [ ] **Step 3: 写 `templates/deployment.yaml` 与 `templates/service.yaml`**

`deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "interview-agent.fullname" . }}
  labels:
    {{- include "interview-agent.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "interview-agent.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        {{- include "interview-agent.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8000
          envFrom:
            - secretRef:
                name: {{ .Values.existingSecret }}
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            initialDelaySeconds: 3
            periodSeconds: 5
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

`service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "interview-agent.fullname" . }}
spec:
  selector:
    {{- include "interview-agent.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: 80
      targetPort: http
```

- [ ] **Step 4: 写 `templates/ingress.yaml` 与 `templates/migration-job.yaml`**

`ingress.yaml`（无域名 → catch-all，直接用 `http://<VPS_IP>/` 暴露，由 Vercel 代理访问）：

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "interview-agent.fullname" . }}
  annotations:
    {{- toYaml .Values.ingress.annotations | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "interview-agent.fullname" . }}
                port:
                  number: 80
{{- end }}
```

`migration-job.yaml`（M0 默认关闭，M1 接 alembic 后打开）：

```yaml
{{- if .Values.migration.enabled }}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "interview-agent.fullname" . }}-migrate
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-1"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 300
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - secretRef:
                name: {{ .Values.existingSecret }}
{{- end }}
```

- [ ] **Step 5: 本地渲染验证**

Run:
```bash
helm lint infra/helm/interview-agent
helm template interview-agent infra/helm/interview-agent --set image.tag=test | head -60
```
Expected: lint 通过；模板渲染出 Deployment / Service / Ingress

- [ ] **Step 6: 提交**

```bash
git add infra/helm
git commit -m "feat(infra): Helm chart（Deployment/Service/Ingress/迁移 Job）"
```

---

## Task 13: GHCR 构建 + 自动部署流水线

**Files:**
- Create: `.github/workflows/deploy.yml`

前置：GitHub 仓库 Secret `KUBE_CONFIG`（Task 11 Step 6 的 base64）。GHCR 镜像名必须全小写。

- [ ] **Step 1: 写 `.github/workflows/deploy.yml`**

```yaml
name: deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  IMAGE: ghcr.io/barclayfu/interview-agent-api

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: backend/Dockerfile
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          build-args: |
            GIT_SHA=${{ github.sha }}
            BUILT_AT=${{ github.event.head_commit.timestamp }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - uses: azure/setup-helm@v4

      - name: Write kubeconfig
        run: |
          mkdir -p "$HOME/.kube"
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > "$HOME/.kube/config"
          chmod 600 "$HOME/.kube/config"

      - name: Helm deploy
        run: |
          helm upgrade --install interview-agent infra/helm/interview-agent \
            --namespace interview-agent --create-namespace \
            --set image.tag=${{ github.sha }} \
            --wait --timeout 5m

      - name: Smoke test
        run: |
          kubectl -n interview-agent rollout status deploy/interview-agent --timeout=120s
          kubectl -n interview-agent get pods
```

- [ ] **Step 2: 推送触发部署**

Run:
```bash
git add .github/workflows/deploy.yml
git commit -m "ci: GHCR 构建 + Helm 部署到 k3s"
git push
```
Expected: Actions 里 `deploy` 绿；GHCR 出现镜像；VPS 上 `sudo k3s kubectl -n interview-agent get pods` 看到 Running

- [ ] **Step 3: 验证公网可达（HTTP）**

Run（本地或 VPS 上）:
```bash
curl -s http://<VPS_IP>/healthz; echo
curl -s http://<VPS_IP>/version; echo
```
Expected: `{"status":"ok"}` 与含 commit sha 的版本信息

- [ ] **Step 4: 验证滚动更新**

Run:
```bash
sudo k3s kubectl -n interview-agent rollout history deploy/interview-agent
```
Expected: 至少一条 revision（后续每次 push 都会新增）

---

## Task 14: Supabase 开通与连接

**Files:** 无（仅本地 `.env`，不入 Git）

- [ ] **Step 1: 建项目（用户操作）**

1. 打开 supabase.com → New project
2. **Region 选 `ap-southeast-1`（新加坡）或 `ap-northeast-1`（东京）**（与 VPS 同区降低延迟）
3. 记下 **database password**、**Project ref**

- [ ] **Step 2: 启用 pgvector**

在 Supabase SQL Editor 执行：

```sql
create extension if not exists vector;
```
Expected: `Success. No rows returned`

- [ ] **Step 3: 取连接串（session pooler，端口 5432）**

Project Settings → Database → Connection string → **Session pooler**，形如：

```
postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres
```

写入本地 `.env`：

```bash
DATABASE_URL=postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres
```

说明：M0 用 **session 模式**（支持预处理语句，`asyncpg` 无需特殊配置）；M1 若遇到连接数压力再评估 transaction 模式（那时需 `statement_cache_size=0`）。

- [ ] **Step 4: 验证**

```bash
make api
curl -s localhost:8000/readyz; echo
```
Expected: `{"db":"ok","redis":"error"}`（Redis 尚未配置，属预期）

- [ ] **Step 5: 无需提交**（`.env` 已在 `.gitignore` 中）

---

## Task 15: Upstash 开通与连接

**Files:** 无（仅本地 `.env`）

- [ ] **Step 1: 建 Redis（用户操作）**

1. 打开 upstash.com → Create Database
2. Region 选 `ap-northeast-1`（东京）或 `ap-southeast-1`（新加坡）
3. TLS 默认开启

- [ ] **Step 2: 取 `rediss://` 连接串并写入 `.env`**

```bash
REDIS_URL=rediss://default:<PASSWORD>@<ENDPOINT>.upstash.io:6379
```

- [ ] **Step 3: 验证**

```bash
make api
curl -s localhost:8000/readyz; echo
```
Expected: `{"db":"ok","redis":"ok"}`

- [ ] **Step 4: 无需提交**

---

## Task 16: 生产密钥（K8s Secret，不入 Git）

**Files:** 无（集群内对象）

- [ ] **Step 1: 在 VPS 上创建 namespace 与 Secret（幂等写法）**

```bash
sudo k3s kubectl create namespace interview-agent --dry-run=client -o yaml | sudo k3s kubectl apply -f -

sudo k3s kubectl -n interview-agent create secret generic interview-agent-secrets \
  --from-literal=APP_ENV=prod \
  --from-literal=DATABASE_URL='postgresql://postgres.<REF>:<PW>@aws-0-<REGION>.pooler.supabase.com:5432/postgres' \
  --from-literal=REDIS_URL='rediss://default:<PW>@<HOST>.upstash.io:6379' \
  --from-literal=LANGFUSE_PUBLIC_KEY='pk-lf-...' \
  --from-literal=LANGFUSE_SECRET_KEY='sk-lf-...' \
  --from-literal=LANGFUSE_BASE_URL='https://cloud.langfuse.com' \
  --from-literal=OTEL_SERVICE_NAME='interview-agent-api' \
  --from-literal=CORS_ORIGINS='https://<PROJECT>.vercel.app' \
  --dry-run=client -o yaml | sudo k3s kubectl apply -f -
```

Expected: `secret/interview-agent-secrets created`（或 `configured`）

- [ ] **Step 2: 确认键齐全**

```bash
sudo k3s kubectl -n interview-agent get secret interview-agent-secrets -o jsonpath='{.data}' | tr ',' '\n'
```
Expected: 列出 8 个键（值不显示明文）

- [ ] **Step 3: 触发一次部署并验证就绪**

```bash
gh workflow run deploy.yml   # 或本地 git push 一个空提交
```
然后：
```bash
sudo k3s kubectl -n interview-agent get pods
curl -s http://<VPS_IP>/readyz; echo
```
Expected: Pod `Running`；`/readyz` 返回 `{"db":"ok","redis":"ok"}`

---

## Task 17: Vercel 部署（前端 + BFF 代理）

**Files:**
- Modify: `README.md`（加线上地址）

- [ ] **Step 1: 导入项目（用户操作）**

1. vercel.com → Add New → Project → 选择 `BarclayFu/interview_agent`
2. **Root Directory 设为 `web`**
3. Framework Preset 自动识别 Next.js

- [ ] **Step 2: 配置环境变量**

Project Settings → Environment Variables（Production 与 Preview 都加）：

```
API_ORIGIN = http://<VPS_IP>
```

说明：`API_ORIGIN` 只用于服务端（SSR + `/api/*` 重写代理），**不需要** `NEXT_PUBLIC_` 前缀；浏览器只访问同源的 `/api/*`。

- [ ] **Step 3: 部署并验证**

访问 `https://<PROJECT>.vercel.app`，应看到：

- 「后端版本（服务端渲染）：<sha>」
- 「DB：ok · Redis：ok」
- 「浏览器直连成功（version=<sha>）」← 这条证明浏览器 → Vercel → API 全链路通了

- [ ] **Step 4: 回填 CORS_ORIGINS（保险起见）**

把 Vercel 域名写进生产 Secret 的 `CORS_ORIGINS`（Task 16 Step 1 的命令重跑一次），这样将来若有跨域调用也不会被拦。

- [ ] **Step 5: 更新 README 并提交**

在 `README.md` 增加：

```markdown
## 线上

- 前端：https://<PROJECT>.vercel.app
- API（仅 HTTP，经 Vercel 代理访问）：http://<VPS_IP>
```

```bash
git add README.md
git commit -m "docs: 补充线上地址"
git push
```

---

## Task 18: 本地 kind 全栈骨架

**Files:**
- Create: `infra/kind/kind-config.yaml`, `infra/kind/deps.yaml`

- [ ] **Step 1: 写 `infra/kind/kind-config.yaml`（多节点）**

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: interview-agent
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

- [ ] **Step 2: 起集群**

Run:
```bash
make kind-up
kubectl get nodes
```
Expected: 3 个节点全部 `Ready`

- [ ] **Step 3: 写 `infra/kind/deps.yaml`（集群内依赖）**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deps
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: deps
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels: { app: postgres }
  template:
    metadata:
      labels: { app: postgres }
    spec:
      containers:
        - name: postgres
          image: pgvector/pgvector:pg16
          env:
            - { name: POSTGRES_USER, value: postgres }
            - { name: POSTGRES_PASSWORD, value: postgres }
            - { name: POSTGRES_DB, value: interview_agent }
          ports: [{ containerPort: 5432 }]
          readinessProbe:
            exec: { command: ["pg_isready", "-U", "postgres"] }
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: deps
spec:
  selector: { app: postgres }
  ports: [{ port: 5432, targetPort: 5432 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: deps
spec:
  replicas: 1
  selector:
    matchLabels: { app: redis }
  template:
    metadata:
      labels: { app: redis }
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports: [{ containerPort: 6379 }]
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: deps
spec:
  selector: { app: redis }
  ports: [{ port: 6379, targetPort: 6379 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: deps
spec:
  replicas: 1
  selector:
    matchLabels: { app: minio }
  template:
    metadata:
      labels: { app: minio }
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          args: ["server", "/data"]
          env:
            - { name: MINIO_ROOT_USER, value: minioadmin }
            - { name: MINIO_ROOT_PASSWORD, value: minioadmin }
          ports: [{ containerPort: 9000 }]
---
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: deps
spec:
  selector: { app: minio }
  ports: [{ port: 9000, targetPort: 9000 }]
```

- [ ] **Step 4: 部署依赖并等就绪**

Run:
```bash
kubectl apply -f infra/kind/deps.yaml
kubectl -n deps rollout status statefulset/postgres --timeout=120s
kubectl -n deps get pods
```
Expected: `postgres` / `redis` / `minio` 均 `Running`

- [ ] **Step 5: 把 app 跑进 kind 并验证**

Run:
```bash
docker build -f backend/Dockerfile -t interview-agent-api:dev .
kind load docker-image interview-agent-api:dev --name interview-agent

kubectl create namespace interview-agent --dry-run=client -o yaml | kubectl apply -f -
kubectl -n interview-agent create secret generic interview-agent-secrets \
  --from-literal=APP_ENV=local-full \
  --from-literal=DATABASE_URL='postgresql://postgres:postgres@postgres.deps.svc.cluster.local:5432/interview_agent' \
  --from-literal=REDIS_URL='redis://redis.deps.svc.cluster.local:6379/0' \
  --from-literal=CORS_ORIGINS='http://localhost:3000' \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install interview-agent infra/helm/interview-agent \
  --namespace interview-agent \
  --set image.repository=interview-agent-api \
  --set image.tag=dev \
  --set image.pullPolicy=Never \
  --set ingress.enabled=false

kubectl -n interview-agent rollout status deploy/interview-agent --timeout=120s
kubectl -n interview-agent port-forward svc/interview-agent 8080:80 &
sleep 2
curl -s localhost:8080/readyz; echo
kill %1
```
Expected: `{"db":"ok","redis":"ok"}`

- [ ] **Step 6: 提交**

```bash
git add infra/kind
git commit -m "feat(infra): 本地 kind 多节点集群与全栈依赖"
```

---

## Task 19: M0 验收与收尾

**Files:**
- Create: `docs/assets/m0/`（截图）
- Modify: `README.md`、`docs/specs/0001-interview-agent-design.md`

- [ ] **Step 1: 逐条过验收清单（对应 M0 spec §3）**

| # | 验收项 | 验证方式 | 结果 |
|---|---|---|---|
| 1 | Vercel 页面显示版本 + DB ✓ / Redis ✓ | 打开线上地址 | ☐ |
| 2 | `/healthz` 200；`/readyz` 200/503 语义正确 | `curl` 两个端点 | ☐ |
| 3 | `/version` 返回 sha 与构建时间 | `curl` | ☐ |
| 4 | CI 绿 + 镜像入 GHCR + k3s 滚动更新成功 | Actions 页面 + `rollout status` | ☐ |
| 5 | 本地 compose 与 kind 均可起 | `make up` / `make kind-up` | ☐ |
| 6 | Langfuse Cloud 能看到 trace | Langfuse UI → Traces | ☐ |
| 7 | 仓库无明文密钥 | `git grep -i "pk-lf-\|sk-lf-\|supabase.co"` 应无结果 | ☐ |
| 8 | VPS 内存稳定在预算内 | `free -h` + `kubectl top pods` | ☐ |

- [ ] **Step 2: 截图归档到 `docs/assets/m0/`**

需要：Vercel 页面、GitHub Actions 绿、GHCR 镜像列表、`kubectl top` / `free -h`、Langfuse trace 详情。

- [ ] **Step 3: 更新 `README.md`**

补充：架构图（可复用设计文档 §3.1 的 mermaid）、本地运行方式（`make up` / `make api` / `make web`）、部署方式（push main 自动部署）、目录结构。

- [ ] **Step 4: 更新设计文档状态**

在 `docs/specs/0001-interview-agent-design.md` 的 M0 小节后追加一行：

```markdown
> M0 状态：✅ 完成（<日期>）。线上：https://<PROJECT>.vercel.app。回顾见 docs/plans/2026-09-20-m0-walking-skeleton.md
```

- [ ] **Step 5: 打 tag 并推送**

```bash
git add README.md docs/
git commit -m "docs: M0 验收完成（README/截图/设计文档状态）"
git tag v0.1.0-m0
git push --follow-tags
```

---

## 计划自检（writing-plans self-review）

**1. Spec 覆盖**：M0 spec §2.1 的 11 项 In Scope 与 §3 的 8 条 DoD 均有对应 Task——脚手架→T1、配置契约→T2、三个端点→T3/T4、Dockerfile→T5、CI→T10、k3s 裁剪→T11、Supabase→T14、Upstash→T15、kind 全栈→T18、Langfuse→T7、密钥→T16、Vercel 与 BFF→T17、验收→T19。评测骨架→T9。

**2. 占位符扫描**：无 "TBD/TODO/稍后补充"；所有需要用户操作的外部步骤（Supabase/Upstash/Vercel/Secret 值）都给出了确切命令与占位符命名规则（`<VPS_IP>` / `<PROJECT_REF>` 等，属运行时填入而非计划缺口）。

**3. 类型/命名一致性**：`Settings.langfuse_base_url`（T2）↔ `LANGFUSE_BASE_URL`（T1/T16）；`check_postgres`/`check_redis`（T4 定义并在 T4 测试中 monkeypatch）；`init_telemetry(settings)`（T7 定义与测试一致）；Helm 的 `existingSecret` 名 `interview-agent-secrets` 在 T12/T16/T18 一致；镜像名 `ghcr.io/barclayfu/interview-agent-api` 在 T12/T13 一致。

**4. 已知未验证项（执行时注意）**：
- Helm pre-upgrade Job 的超时行为（M0 默认关闭，M1 打开时验证）
- Traefik IngressClass 名称：执行 T12 后跑 `kubectl get ingressclass` 确认是 `traefik`
- kind 三节点对本机资源有要求（建议 ≥ 8GB 可用内存）
