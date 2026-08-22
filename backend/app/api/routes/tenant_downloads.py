from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_company_access, get_tenant_context_dep, get_tenant_db, require_permission
from app.core.errors import APIError
from app.core.tenant_context import TenantContext
from app.models.tenant import CNABRemittance
from app.providers.storage import S3StorageProvider
from app.schemas.auth import AuthUser

router = APIRouter(prefix="/api/v1", tags=["Financeiro - Downloads"])
storage = S3StorageProvider()


@router.get("/cnab/remittances/{remittance_id}/download")
async def download_cnab_remittance(
    remittance_id: UUID,
    context: TenantContext = Depends(get_tenant_context_dep),
    user: AuthUser = Depends(require_permission("cnab.generate")),
    session: AsyncSession = Depends(get_tenant_db),
) -> Response:
    remittance = await session.get(CNABRemittance, remittance_id)
    if remittance is None:
        raise APIError("CNAB_REMITTANCE_NOT_FOUND", "Remessa CNAB não encontrada.", 404)

    ensure_company_access(user, remittance.company_id)
    content = await storage.get_bytes(context.storage_bucket, remittance.object_key)
    filename = Path(remittance.object_key).name or f"remessa-{remittance.sequence:06d}.REM"

    return Response(
        content=content,
        media_type="text/plain; charset=latin-1",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
