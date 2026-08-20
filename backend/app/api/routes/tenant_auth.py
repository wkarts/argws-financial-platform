from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_tenant_user, get_tenant_context_dep, get_tenant_db
from app.core.tenant_context import TenantContext
from app.schemas.auth import AuthUser, LoginRequest, RefreshRequest, TokenPair
from app.schemas.common import SuccessResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Tenant - Auth"])
service = AuthService()


@router.post("/login", response_model=SuccessResponse[dict])
async def login(
    payload: LoginRequest,
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    tokens, user = await service.login_tenant(session, context.tenant_id, payload.email, payload.password)
    return SuccessResponse(
        data={
            "tokens": tokens.model_dump(),
            "user": user.model_dump(),
            "tenant": {
                "id": context.tenant_id,
                "slug": context.slug,
                "hostname": context.hostname,
                "timezone": context.timezone,
            },
        }
    )


@router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(
    payload: RefreshRequest,
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[TokenPair]:
    return SuccessResponse(data=await service.refresh_tenant(session, context.tenant_id, payload.refresh_token))


@router.get("/me", response_model=SuccessResponse[AuthUser])
async def me(user: AuthUser = Depends(current_tenant_user)) -> SuccessResponse[AuthUser]:
    return SuccessResponse(data=user)


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    payload: RefreshRequest,
    user: AuthUser = Depends(current_tenant_user),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    await service.logout_tenant(session, user.id, payload.refresh_token)
    return SuccessResponse(data={"revoked": True})
