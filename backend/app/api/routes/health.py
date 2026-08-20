from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.api.deps import get_redis
from app.core.config import settings
from app.db.platform import get_platform_session
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, checks={"process": "ok"})


@router.get("/health/ready", response_model=HealthResponse)
async def ready(
    response: Response,
    session: AsyncSession = Depends(get_platform_session),
    redis: Redis = Depends(get_redis),
) -> HealthResponse:
    checks: dict[str, str] = {}
    status = "ok"
    try:
        await session.execute(text("select 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"error:{type(exc).__name__}"
        status = "error"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error:{type(exc).__name__}"
        status = "error"
    try:
        broker = urlparse(settings.rabbitmq_url)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(broker.hostname or "financial-rabbitmq", broker.port or 5672), timeout=3
        )
        writer.close()
        await writer.wait_closed()
        checks["rabbitmq"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["rabbitmq"] = f"error:{type(exc).__name__}"
        status = "error"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(settings.s3_endpoint_url.rstrip("/") + "/minio/health/live")
            response.raise_for_status()
        checks["minio"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["minio"] = f"error:{type(exc).__name__}"
        status = "error"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, version=__version__, checks=checks)


@router.get("/health", response_model=HealthResponse)
async def health(
    response: Response,
    session: AsyncSession = Depends(get_platform_session),
    redis: Redis = Depends(get_redis),
) -> HealthResponse:
    return await ready(response, session, redis)


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not settings.prometheus_enabled:
        return Response(status_code=404)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
