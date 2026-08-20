from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import APIError
from app.core.security import create_token, decode_token, hash_api_key, verify_password
from app.models.platform import PlatformRefreshToken, PlatformUser
from app.models.tenant import TenantRefreshToken, TenantUser, UserCompany
from app.schemas.auth import AuthUser, TokenPair


class AuthService:
    @staticmethod
    def _token_pair(
        *, user_id: str, audience: str, role: str, tenant_id: str | None = None, permissions: list[str] | None = None
    ) -> TokenPair:
        access = create_token(
            subject=user_id,
            audience=audience,  # type: ignore[arg-type]
            token_type="access",
            tenant_id=tenant_id,
            roles=[role],
            extra={"permissions": permissions or []},
        )
        refresh = create_token(
            subject=user_id,
            audience=audience,  # type: ignore[arg-type]
            token_type="refresh",
            tenant_id=tenant_id,
            roles=[role],
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_minutes * 60,
        )

    async def login_control(self, session: AsyncSession, email: str, password: str) -> tuple[TokenPair, AuthUser]:
        user = await session.scalar(select(PlatformUser).where(PlatformUser.email == email.lower()))
        if user is None or not user.is_active:
            raise APIError("INVALID_CREDENTIALS", "E-mail ou senha inválidos.", 401)
        now = datetime.now(UTC)
        if user.locked_until and user.locked_until > now:
            raise APIError("ACCOUNT_LOCKED", "Conta temporariamente bloqueada.", 423)
        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.login_max_attempts:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            await session.commit()
            raise APIError("INVALID_CREDENTIALS", "E-mail ou senha inválidos.", 401)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        pair = self._token_pair(user_id=str(user.id), audience="control", role=user.role)
        session.add(
            PlatformRefreshToken(
                user_id=user.id,
                token_hash=hash_api_key(pair.refresh_token),
                expires_at=now + timedelta(days=settings.refresh_token_days),
            )
        )
        await session.commit()
        return pair, AuthUser(id=str(user.id), name=user.name, email=user.email, role=user.role)

    async def login_tenant(
        self, session: AsyncSession, tenant_id: str, email: str, password: str
    ) -> tuple[TokenPair, AuthUser]:
        user = await session.scalar(select(TenantUser).where(TenantUser.email == email.lower()))
        if user is None or not user.is_active:
            raise APIError("INVALID_CREDENTIALS", "E-mail ou senha inválidos.", 401)
        now = datetime.now(UTC)
        if user.locked_until and user.locked_until > now:
            raise APIError("ACCOUNT_LOCKED", "Conta temporariamente bloqueada.", 423)
        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.login_max_attempts:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            await session.commit()
            raise APIError("INVALID_CREDENTIALS", "E-mail ou senha inválidos.", 401)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        company_ids = [
            str(item)
            for item in (await session.scalars(select(UserCompany.company_id).where(UserCompany.user_id == user.id))).all()
        ]
        pair = self._token_pair(
            user_id=str(user.id),
            audience="tenant",
            role=user.role,
            tenant_id=tenant_id,
            permissions=user.permissions,
        )
        session.add(
            TenantRefreshToken(
                user_id=user.id,
                token_hash=hash_api_key(pair.refresh_token),
                expires_at=now + timedelta(days=settings.refresh_token_days),
            )
        )
        await session.commit()
        return pair, AuthUser(
            id=str(user.id),
            name=user.name,
            email=user.email,
            role=user.role,
            permissions=user.permissions,
            companies=company_ids,
        )

    async def refresh_control(self, session: AsyncSession, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, "control", "refresh")
        stored = await session.scalar(
            select(PlatformRefreshToken).where(
                PlatformRefreshToken.token_hash == hash_api_key(refresh_token),
                PlatformRefreshToken.revoked_at.is_(None),
                PlatformRefreshToken.expires_at > datetime.now(UTC),
            )
        )
        if stored is None:
            raise APIError("REFRESH_TOKEN_REVOKED", "Refresh token inválido ou revogado.", 401)
        user = await session.get(PlatformUser, UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise APIError("USER_NOT_ACTIVE", "Usuário não está ativo.", 401)
        stored.revoked_at = datetime.now(UTC)
        pair = self._token_pair(user_id=str(user.id), audience="control", role=user.role)
        session.add(
            PlatformRefreshToken(
                user_id=user.id,
                token_hash=hash_api_key(pair.refresh_token),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        await session.commit()
        return pair

    async def refresh_tenant(self, session: AsyncSession, tenant_id: str, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, "tenant", "refresh")
        if payload.get("tenant_id") != tenant_id:
            raise APIError("TENANT_TOKEN_MISMATCH", "Token não pertence a este tenant.", 403)
        stored = await session.scalar(
            select(TenantRefreshToken).where(
                TenantRefreshToken.token_hash == hash_api_key(refresh_token),
                TenantRefreshToken.revoked_at.is_(None),
                TenantRefreshToken.expires_at > datetime.now(UTC),
            )
        )
        if stored is None:
            raise APIError("REFRESH_TOKEN_REVOKED", "Refresh token inválido ou revogado.", 401)
        user = await session.get(TenantUser, UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise APIError("USER_NOT_ACTIVE", "Usuário não está ativo.", 401)
        stored.revoked_at = datetime.now(UTC)
        pair = self._token_pair(
            user_id=str(user.id),
            audience="tenant",
            role=user.role,
            tenant_id=tenant_id,
            permissions=user.permissions,
        )
        session.add(
            TenantRefreshToken(
                user_id=user.id,
                token_hash=hash_api_key(pair.refresh_token),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        await session.commit()
        return pair

    async def logout_control(self, session: AsyncSession, user_id: str, refresh_token: str) -> None:
        stored = await session.scalar(
            select(PlatformRefreshToken).where(
                PlatformRefreshToken.user_id == UUID(user_id),
                PlatformRefreshToken.token_hash == hash_api_key(refresh_token),
                PlatformRefreshToken.revoked_at.is_(None),
            )
        )
        if stored is not None:
            stored.revoked_at = datetime.now(UTC)
            await session.commit()

    async def logout_tenant(self, session: AsyncSession, user_id: str, refresh_token: str) -> None:
        stored = await session.scalar(
            select(TenantRefreshToken).where(
                TenantRefreshToken.user_id == UUID(user_id),
                TenantRefreshToken.token_hash == hash_api_key(refresh_token),
                TenantRefreshToken.revoked_at.is_(None),
            )
        )
        if stored is not None:
            stored.revoked_at = datetime.now(UTC)
            await session.commit()
