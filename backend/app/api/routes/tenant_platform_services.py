from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import get_tenant_context_dep, require_permission
from app.core.config import settings
from app.core.tenant_context import TenantContext
from app.db.platform import PlatformSessionLocal
from app.models.platform import PlatformIntegration, Tenant
from app.schemas.auth import AuthUser
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/api/v1", tags=["Serviços da plataforma"])


@router.get("/platform-services", response_model=SuccessResponse[dict])
async def platform_services(
    context: TenantContext = Depends(get_tenant_context_dep),
    _: AuthUser = Depends(require_permission("integrations.read")),
) -> SuccessResponse[dict]:
    async with PlatformSessionLocal() as session:
        tenant = await session.get(Tenant, UUID(context.tenant_id))
        features = dict(tenant.features or {}) if tenant else {}
        integrations = {
            item.provider: item
            for item in (
                await session.scalars(
                    select(PlatformIntegration).where(
                        PlatformIntegration.provider.in_(["EVOLUTION", "SMTP"])
                    )
                )
            ).all()
        }

    whatsapp_global = integrations.get("EVOLUTION")
    smtp_global = integrations.get("SMTP")
    whatsapp_configured = bool(
        (
            whatsapp_global
            and whatsapp_global.is_enabled
            and whatsapp_global.encrypted_secrets
            and whatsapp_global.public_config.get("base_url")
        )
        or (settings.evolution_enabled and settings.evolution_base_url and settings.evolution_api_key)
    )
    email_configured = bool(
        (smtp_global and smtp_global.is_enabled and smtp_global.public_config.get("host"))
        or (settings.smtp_enabled and settings.smtp_host)
    )
    whatsapp_enabled = bool(features.get("whatsapp_enabled", True)) and whatsapp_configured

    return SuccessResponse(
        data={
            "whatsapp": {
                "label": "WhatsApp",
                "managed": True,
                "available": whatsapp_enabled,
                "configured_by_platform": whatsapp_configured,
                "billing_mode": str(features.get("whatsapp_billing_mode", "INCLUDED")),
                "monthly_price": features.get("whatsapp_monthly_price"),
            },
            "email": {
                "label": "E-mail",
                "managed": True,
                "available": email_configured,
                "configured_by_platform": email_configured,
            },
            "custom_integrations_allowed": bool(features.get("custom_integrations_allowed", True)),
        }
    )
