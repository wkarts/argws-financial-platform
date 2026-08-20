from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import accessible_company_ids, ensure_company_access
from app.core.config import settings
from app.core.errors import APIError
from app.core.security import decode_token
from app.core.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from app.db.platform import get_platform_session
from app.db.tenant import tenant_session
from app.models.platform import PlatformUser
from app.models.tenant import TenantUser, UserCompany
from app.schemas.auth import AuthUser
from app.services.tenant_resolver import TenantResolver

bearer = HTTPBearer(auto_error=False)
_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def request_hostname(request: Request) -> str:
    host = request.headers.get("host", "")
    if settings.app_env in {"development", "testing"} and settings.allow_dev_tenant_header:
        host = request.headers.get("x-tenant-host", host)
    return TenantResolver.normalize_hostname(host)


async def ensure_control_plane_host(request: Request) -> None:
    if settings.app_env in {"development", "testing"}:
        return
    host = request_hostname(request)
    if host != settings.control_plane_host.lower():
        raise APIError("CONTROL_PLANE_HOST_REQUIRED", "Endpoint exclusivo do Control Plane.", 404)


async def get_tenant_context_dep(
    request: Request,
    platform_session: AsyncSession = Depends(get_platform_session),
    redis: Redis = Depends(get_redis),
) -> AsyncIterator[TenantContext]:
    host = request_hostname(request)
    if host == settings.control_plane_host.lower():
        raise APIError("TENANT_HOST_REQUIRED", "Este endpoint exige domínio de tenant.", 404)
    resolver = TenantResolver(platform_session, redis)
    context = await resolver.resolve(host)
    token = set_tenant_context(context)
    request.state.tenant = context
    try:
        yield context
    finally:
        reset_tenant_context(token)


async def get_tenant_db(
    context: TenantContext = Depends(get_tenant_context_dep),
) -> AsyncIterator[AsyncSession]:
    async for session in tenant_session(context):
        yield session


def token_or_error(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError("AUTHENTICATION_REQUIRED", "Autenticação obrigatória.", 401)
    return credentials.credentials


async def current_control_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_platform_session),
) -> AuthUser:
    await ensure_control_plane_host(request)
    payload = decode_token(token_or_error(credentials), "control")
    user = await session.get(PlatformUser, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise APIError("USER_NOT_ACTIVE", "Usuário do Control Plane não está ativo.", 401)
    return AuthUser(id=str(user.id), name=user.name, email=user.email, role=user.role)


async def current_tenant_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
) -> AuthUser:
    payload = decode_token(token_or_error(credentials), "tenant")
    if payload.get("tenant_id") != context.tenant_id:
        raise APIError("TENANT_TOKEN_MISMATCH", "Token não pertence ao domínio acessado.", 403)
    user = await session.get(TenantUser, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise APIError("USER_NOT_ACTIVE", "Usuário não está ativo.", 401)
    company_ids = [
        str(company_id)
        for company_id in (
            await session.scalars(select(UserCompany.company_id).where(UserCompany.user_id == user.id))
        ).all()
    ]
    return AuthUser(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
        permissions=user.permissions,
        companies=company_ids,
    )


def require_control_roles(*roles: str) -> Callable[..., AuthUser]:
    async def dependency(user: AuthUser = Depends(current_control_user)) -> AuthUser:
        if user.role not in roles and user.role != "PLATFORM_SUPERADMIN":
            raise APIError("FORBIDDEN", "Permissão insuficiente no Control Plane.", 403)
        return user
    return dependency


def require_permission(permission: str) -> Callable[..., AuthUser]:
    async def dependency(user: AuthUser = Depends(current_tenant_user)) -> AuthUser:
        if user.role == "TENANT_ADMIN" or "*" in user.permissions or permission in user.permissions:
            return user
        raise APIError("FORBIDDEN", "Permissão insuficiente.", 403, {"required": permission})
    return dependency


