from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse
from starlette.responses import JSONResponse

from app.core.rate_limit import consume_rate_limit, parse_rate_limit, request_identity, request_scope

from app import __version__
from app.api.deps import close_redis
from app.api.routes import (
    control_auth,
    control_management,
    control_operations,
    control_tenants,
    health,
    tenant_auth,
    tenant_admin,
    tenant_catalog,
    tenant_downloads,
    tenant_finance,
    tenant_integrations,
    tenant_management,
    tenant_imports,
    tenant_operations,
    tenant_pix_automatic,
    tenant_platform_services,
    public_finance,
    webhooks,
)
from app.core.config import settings
from app.core.errors import APIError, api_error_handler
from app.core.logging import configure_logging
from app.db.platform import platform_engine
from app.db.tenant import tenant_engines

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_started", version=__version__, environment=settings.app_env)
    yield
    await close_redis()
    await tenant_engines.dispose_all()
    await platform_engine.dispose()
    logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Plataforma SaaS financeira multitenant para cobranças e recebíveis.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

configured_hosts = [f"*{item}" if item.startswith(".") else item for item in settings.trusted_host_list]
allowed_hosts = sorted(set(configured_hosts) | {"financial-api", "localhost", "127.0.0.1"})
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts or ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-Host", "X-Webhook-Secret", "X-API-Key", "X-Platform-API-Key"],
)


@app.middleware("http")
async def rate_limit_guard(request: Request, call_next):
    if request.url.path.startswith(("/health", "/metrics")):
        return await call_next(request)
    try:
        from app.api.deps import get_redis

        rule = parse_rate_limit(settings.rate_limit_default)
        redis = await get_redis()
        identity = request_identity(request)
        scope = request_scope(request)
        window = int(__import__("time").time()) // rule.window_seconds
        key = f"rate-limit:{scope}:{identity}:{window}"
        allowed, remaining, retry_after = await consume_rate_limit(redis, key=key, rule=rule)
    except Exception as exc:
        logger.warning("rate_limit_unavailable", error=type(exc).__name__)
        return await call_next(request)
    if not allowed:
        return ORJSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Limite de requisições excedido.",
                    "details": {"retry_after": retry_after},
                },
            },
            headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rule.limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.middleware("http")
async def maintenance_guard(request: Request, call_next):
    if request.url.path.startswith(("/health", "/metrics")):
        return await call_next(request)

    try:
        maintenance_enabled = settings.maintenance_file.exists()
    except OSError as exc:
        logger.error(
            "maintenance_file_unavailable",
            path=str(settings.maintenance_file),
            error=type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "MAINTENANCE_STATE_UNAVAILABLE",
                    "message": "Não foi possível validar o estado de manutenção da plataforma.",
                }
            },
            headers={"Retry-After": "60"},
        )

    if maintenance_enabled:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "MAINTENANCE_MODE", "message": "Plataforma temporariamente indisponível para manutenção."}},
            headers={"Retry-After": "300"},
        )
    return await call_next(request)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed")
        raise
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]

app.include_router(health.router)
app.include_router(control_auth.router)
app.include_router(control_management.router)
app.include_router(control_operations.router)
app.include_router(control_tenants.router)
app.include_router(tenant_auth.router)
app.include_router(tenant_admin.router)
app.include_router(tenant_catalog.router)
app.include_router(tenant_downloads.router)
app.include_router(tenant_finance.router)
app.include_router(tenant_integrations.router)
app.include_router(tenant_management.router)
app.include_router(tenant_imports.router)
app.include_router(tenant_operations.router)
app.include_router(tenant_pix_automatic.router)
app.include_router(tenant_platform_services.router)
app.include_router(public_finance.router)
app.include_router(webhooks.router)


@app.get("/api", tags=["Platform"])
async def api_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.app_env,
        "docs": "/api/docs",
    }
