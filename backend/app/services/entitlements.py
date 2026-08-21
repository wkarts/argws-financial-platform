from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.platform import Tenant


@dataclass(frozen=True, slots=True)
class TenantEntitlements:
    tenant_id: UUID
    plan_code: str
    features: dict[str, Any]
    limits: dict[str, Any]

    def require_feature(self, feature: str) -> None:
        value = self.features.get(feature)
        if value is False:
            raise APIError(
                "FEATURE_NOT_AVAILABLE",
                "Este recurso não está habilitado no plano do tenant.",
                403,
                {"feature": feature, "plan": self.plan_code},
            )

    def enforce_limit(self, resource: str, current: int, increment: int = 1) -> None:
        raw = self.limits.get(resource)
        if raw in (None, "", 0, "0"):
            return
        try:
            limit = int(raw)
        except (TypeError, ValueError):
            return
        if limit > 0 and current + increment > limit:
            raise APIError(
                "TENANT_LIMIT_EXCEEDED",
                "O limite contratado para este recurso foi atingido.",
                409,
                {
                    "resource": resource,
                    "current": current,
                    "increment": increment,
                    "limit": limit,
                    "plan": self.plan_code,
                },
            )


async def load_tenant_entitlements(session: AsyncSession, tenant_id: str) -> TenantEntitlements:
    item = await session.get(Tenant, UUID(tenant_id))
    if item is None:
        raise APIError("TENANT_NOT_FOUND", "Tenant não encontrado no Control Plane.", 404)
    if item.status != "ACTIVE":
        raise APIError("TENANT_NOT_ACTIVE", "Tenant não está ativo.", 403, {"status": item.status})
    return TenantEntitlements(
        tenant_id=item.id,
        plan_code=item.plan_code,
        features=dict(item.features or {}),
        limits=dict(item.limits or {}),
    )
