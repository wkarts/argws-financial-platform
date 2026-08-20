from __future__ import annotations

import secrets
from datetime import UTC, datetime

import dns.asyncresolver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import APIError
from app.models.platform import Tenant, TenantDomain
from app.providers.cloudflare import CloudflareDNSProvider


class DomainService:
    def __init__(self) -> None:
        self.cloudflare = CloudflareDNSProvider()

    async def add_custom_domain(
        self, session: AsyncSession, tenant: Tenant, hostname: str, is_primary: bool = False
    ) -> TenantDomain:
        hostname = hostname.lower().strip().rstrip(".")
        if hostname == settings.control_plane_host or hostname.endswith(f".{settings.control_plane_host}"):
            raise APIError("RESERVED_DOMAIN", "Este domínio é reservado ao Control Plane.", 422)
        if await session.scalar(select(TenantDomain.id).where(TenantDomain.hostname == hostname)):
            raise APIError("DOMAIN_ALREADY_EXISTS", "Este domínio já está vinculado à plataforma.", 409)
        if is_primary:
            for item in tenant.domains:
                item.is_primary = False
        domain = TenantDomain(
            tenant_id=tenant.id,
            hostname=hostname,
            domain_type="CUSTOM",
            status="VERIFYING",
            is_primary=is_primary,
            is_temporary=False,
            verification_token=secrets.token_urlsafe(32),
        )
        session.add(domain)
        await session.commit()
        await session.refresh(domain)
        return domain

    async def verify(self, session: AsyncSession, domain: TenantDomain) -> TenantDomain:
        expected = (settings.cloudflare_tenant_record_target or settings.platform_domain).rstrip(".").lower()
        domain.last_checked_at = datetime.now(UTC)
        try:
            answers = await dns.asyncresolver.resolve(domain.hostname, "CNAME")
            targets = {str(item.target).rstrip(".").lower() for item in answers}
            if expected not in targets:
                raise APIError(
                    "DOMAIN_CNAME_MISMATCH",
                    "O CNAME ainda não aponta para o gateway da plataforma.",
                    409,
                    {"expected": expected, "found": sorted(targets)},
                )
            domain.dns_verified_at = datetime.now(UTC)
            domain.status = "WAITING_SSL" if settings.public_scheme == "https" else "ACTIVE"
            domain.last_error = None
        except APIError:
            raise
        except Exception as exc:
            domain.status = "VERIFYING"
            domain.last_error = str(exc)[:2000]
            await session.commit()
            raise APIError(
                "DOMAIN_DNS_NOT_READY",
                "O DNS do domínio ainda não está propagado ou está incorreto.",
                409,
                {"hostname": domain.hostname},
            ) from exc
        await session.commit()
        return domain

    async def mark_ssl_active(self, session: AsyncSession, domain: TenantDomain) -> TenantDomain:
        if domain.dns_verified_at is None:
            raise APIError("DOMAIN_DNS_NOT_VERIFIED", "Verifique o DNS antes de ativar o SSL.", 409)
        domain.ssl_status = "ACTIVE"
        domain.ssl_issued_at = datetime.now(UTC)
        domain.status = "ACTIVE"
        domain.last_error = None
        await session.commit()
        return domain


domain_service = DomainService()
