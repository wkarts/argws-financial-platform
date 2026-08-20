from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import Request

if TYPE_CHECKING:
    from redis.asyncio import Redis
else:
    Redis = Any

_RATE_RE = re.compile(r"^(?P<limit>[1-9][0-9]*)/(?P<period>second|minute|hour|day)s?$", re.IGNORECASE)
_PERIOD_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass(frozen=True, slots=True)
class RateLimit:
    limit: int
    window_seconds: int


def parse_rate_limit(value: str) -> RateLimit:
    match = _RATE_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"Rate limit inválido: {value!r}. Use, por exemplo, 120/minute.")
    period = match.group("period").lower()
    return RateLimit(limit=int(match.group("limit")), window_seconds=_PERIOD_SECONDS[period])


def request_scope(request: Request) -> str:
    path = request.url.path
    if "/auth/login" in path:
        return "auth-login"
    if "/webhooks/" in path:
        return "webhook"
    if path.startswith("/api/control/"):
        return "control"
    return "tenant"


def request_identity(request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    host = request.headers.get("host", "unknown").split(":", maxsplit=1)[0].lower()
    return f"{host}:{client}"


async def consume_rate_limit(
    redis: Redis,
    *,
    key: str,
    rule: RateLimit,
) -> tuple[bool, int, int]:
    """Consome uma posição em janela fixa e retorna permitido, restante e TTL.

    O pipeline evita uma chave sem expiração na operação normal. Caso o processo
    falhe entre INCR e EXPIRE, a chamada seguinte corrige o TTL ausente.
    """

    count = int(await redis.incr(key))
    ttl = int(await redis.ttl(key))
    if count == 1 or ttl < 0:
        await redis.expire(key, rule.window_seconds)
        ttl = rule.window_seconds
    return count <= rule.limit, max(rule.limit - count, 0), max(ttl, 0)
