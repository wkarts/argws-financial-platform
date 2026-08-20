from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_control_user, ensure_control_plane_host
from app.db.platform import get_platform_session
from app.schemas.auth import AuthUser, LoginRequest, RefreshRequest, TokenPair
from app.schemas.common import SuccessResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/control/v1/auth", tags=["Control Plane - Auth"])
service = AuthService()


@router.post("/login", response_model=SuccessResponse[dict])
async def login(
    request: Request,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_platform_session),
) -> SuccessResponse[dict]:
    await ensure_control_plane_host(request)
    tokens, user = await service.login_control(session, payload.email, payload.password)
    return SuccessResponse(data={"tokens": tokens.model_dump(), "user": user.model_dump()})


@router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(
    request: Request,
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_platform_session),
) -> SuccessResponse[TokenPair]:
    await ensure_control_plane_host(request)
    return SuccessResponse(data=await service.refresh_control(session, payload.refresh_token))


@router.get("/me", response_model=SuccessResponse[AuthUser])
async def me(user: AuthUser = Depends(current_control_user)) -> SuccessResponse[AuthUser]:
    return SuccessResponse(data=user)


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    payload: RefreshRequest,
    user: AuthUser = Depends(current_control_user),
    session: AsyncSession = Depends(get_platform_session),
) -> SuccessResponse[dict]:
    await service.logout_control(session, user.id, payload.refresh_token)
    return SuccessResponse(data={"revoked": True})
