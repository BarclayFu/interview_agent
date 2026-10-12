"""X-Proxy-Secret 校验（spec §5.7）。

- 仅保护业务前缀 /resumes /sessions；/healthz /readyz /version 公开（K8s probe 需要）。
- PROXY_SECRET 未配置时不强制（本地开发便利）；生产经由 K8s Secret 必配。
- 纯 ASGI 实现（不用 BaseHTTPMiddleware）：后者包一层缓冲层，对 SSE 流式有已知干扰。
"""

import json

from starlette.types import ASGIApp, Receive, Scope, Send

PROTECTED_PREFIXES = ("/resumes", "/sessions")


class ProxySecretMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from interview_agent.core.config import get_settings

        secret = get_settings().proxy_secret
        path: str = scope["path"]
        if secret and path.startswith(PROTECTED_PREFIXES):
            headers = dict(scope["headers"])
            if headers.get(b"x-proxy-secret", b"").decode() != secret:
                body = json.dumps({"detail": "invalid proxy secret"}).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)
