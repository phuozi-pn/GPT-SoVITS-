"""
基于 Redis 的令牌桶限流中间件。

策略:
  - /auth/sms/send   → 每手机号 1 req/min，每 IP 5 req/min
  - /auth/login      → 每手机号 3 req/min，每 IP 10 req/min
  - /synthesis       → 每用户 30 req/min
  - /open/synthesis  → 每 API Key 60 req/min

通过 REDIS_URL 环境变量获取 Redis 连接。
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from redis import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from voice_platform.config import get_settings

logger = logging.getLogger(__name__)

# ── 限流规则 ──────────────────────────────────────────────

_RATE_LIMIT_RULES: dict[str, dict[str, int]] = {
    "/auth/sms/send": {"per_phone": 1, "per_ip": 5},
    "/auth/login": {"per_phone": 3, "per_ip": 10},
    "/synthesis": {"per_user": 30},
    "/open/synthesis": {"per_api_key": 60},
}

_WINDOW_SEC = 60  # 所有规则均为 60 秒窗口


def _redis_client() -> Redis | None:
    """获取 Redis 客户端（失败返回 None，降级跳过限流）。"""
    try:
        settings = get_settings()
        return Redis.from_url(settings.redis_url, socket_timeout=2, decode_responses=True)
    except Exception as exc:
        logger.warning("RateLimiter: Redis unavailable, skipping. %s", exc)
        return None


def _check_token_bucket(
    client: Redis,
    key: str,
    max_tokens: int,
    window_sec: int = _WINDOW_SEC,
) -> bool:
    """
    令牌桶算法: key 在 window_sec 内最多允许 max_tokens 次请求。
    返回 True 表示允许，False 表示限流。
    """
    now = time.time()
    window_start = now - window_sec

    with client.pipeline() as pipe:
        pipe.zremrangebyscore(key, 0, window_start)  # 移除过期令牌
        pipe.zcard(key)  # 当前窗口内令牌数
        pipe.zadd(key, {str(now): now})  # 添加新令牌
        pipe.expire(key, window_sec + 10)  # 设置过期
        _, count, _, _ = pipe.execute()

    return int(count) < max_tokens


def _extract_phone(body_json: dict | None) -> str | None:
    """从请求体中提取 phone 字段。"""
    if not body_json:
        return None
    phone = body_json.get("phone")
    return phone if phone else None


def _extract_client_ip(request: Request) -> str:
    """提取客户端 IP（优先 X-Forwarded-For）。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "127.0.0.1"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """令牌桶限流中间件 — 仅对配置的路径生效。"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # 规范化路径：移除 /api/v1 前缀
        normalized = path
        if path.startswith("/api/v1"):
            normalized = path[len("/api/v1"):]

        rule = _RATE_LIMIT_RULES.get(normalized)
        if not rule:
            return await call_next(request)

        client = _redis_client()
        if not client:
            # Redis 不可用 → 降级放行
            return await call_next(request)

        try:
            # 尝试读取请求体（不消耗流）
            body_json: dict | None = None
            try:
                body_json = await request.json()
            except Exception:
                pass

            limited = self._apply_rule(client, rule, request, body_json)
            if limited:
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后再试。",
                        "details": {"retry_after_sec": _WINDOW_SEC},
                    },
                )
        finally:
            client.close()

        return await call_next(request)

    def _apply_rule(
        self,
        client: Redis,
        rule: dict,
        request: Request,
        body_json: dict | None,
    ) -> bool:
        """逐一检查限流规则，任意一条触发即返回 True。"""
        now_ts = int(time.time())

        if "per_phone" in rule:
            phone = _extract_phone(body_json)
            if phone:
                key = f"rl:phone:{request.url.path}:{phone}"
                if not _check_token_bucket(client, key, rule["per_phone"]):
                    logger.warning("RateLimited phone=%s path=%s", phone[-4:], request.url.path)
                    return True

        if "per_ip" in rule:
            ip = _extract_client_ip(request)
            key = f"rl:ip:{request.url.path}:{ip}"
            if not _check_token_bucket(client, key, rule["per_ip"]):
                logger.warning("RateLimited ip=%s path=%s", ip, request.url.path)
                return True

        if "per_user" in rule:
            user_id = request.headers.get("X-User-Id") or body_json.get("user_id") if body_json else None
            if user_id:
                key = f"rl:user:{request.url.path}:{user_id}"
                if not _check_token_bucket(client, key, rule["per_user"]):
                    logger.warning("RateLimited user=%s path=%s", user_id, request.url.path)
                    return True

        if "per_api_key" in rule:
            api_key = request.headers.get("X-Api-Key")
            if api_key:
                key = f"rl:apikey:{request.url.path}:{api_key}"
                if not _check_token_bucket(client, key, rule["per_api_key"]):
                    logger.warning("RateLimited api_key=%s path=%s", api_key[:8], request.url.path)
                    return True

        return False
