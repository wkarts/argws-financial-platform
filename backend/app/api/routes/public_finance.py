from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_context_dep, get_tenant_db
from app.core.errors import APIError
from app.core.security import hash_api_key
from app.core.tenant_context import TenantContext
from app.models.tenant import Charge, Company, Customer, PublicPaymentLink, Receivable
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/api/public/v1", tags=["Portal público de cobrança"])


@router.get("/payment-links/{token}", response_model=SuccessResponse[dict])
async def public_payment_link(
    token: str,
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    if len(token) < 24:
        raise APIError("PAYMENT_LINK_INVALID", "Link de pagamento inválido.", 404)
    item = await session.scalar(
        select(PublicPaymentLink).where(
            PublicPaymentLink.token_hash == hash_api_key(token),
            PublicPaymentLink.is_active.is_(True),
        ).with_for_update()
    )
    if item is None:
        raise APIError("PAYMENT_LINK_NOT_FOUND", "Link de pagamento inválido ou desativado.", 404)
    now = datetime.now(UTC)
    if item.expires_at and item.expires_at <= now:
        item.is_active = False
        await session.commit()
        raise APIError("PAYMENT_LINK_EXPIRED", "Este link de pagamento expirou.", 410)
    if item.max_views is not None and item.view_count >= item.max_views:
        item.is_active = False
        await session.commit()
        raise APIError("PAYMENT_LINK_LIMIT_REACHED", "Este link atingiu o limite de acessos.", 410)
    receivable = await session.get(Receivable, item.receivable_id)
    if receivable is None:
        raise APIError("RECEIVABLE_NOT_FOUND", "Cobrança não encontrada.", 404)
    company = await session.get(Company, receivable.company_id)
    customer = await session.get(Customer, receivable.customer_id)
    if company is None or customer is None:
        raise APIError("PAYMENT_LINK_INCOMPLETE", "Dados da cobrança estão incompletos.", 409)
    charge = await session.scalar(
        select(Charge)
        .where(Charge.receivable_id == receivable.id, Charge.status.notin_(["CANCELLED", "FAILED", "EXPIRED"]))
        .order_by(Charge.created_at.desc())
    )
    item.view_count += 1
    item.last_viewed_at = now
    await session.commit()
    masked_document = customer.tax_id or ""
    if len(masked_document) > 4:
        masked_document = "*" * (len(masked_document) - 4) + masked_document[-4:]
    return SuccessResponse(
        data={
            "tenant": {"slug": context.slug, "hostname": context.hostname},
            "company": {
                "name": company.trade_name or company.legal_name,
                "tax_id": company.tax_id,
                "branding": company.branding,
            },
            "customer": {"name": customer.name, "document": masked_document},
            "receivable": {
                "id": str(receivable.id),
                "document_number": receivable.document_number,
                "description": receivable.description,
                "competence": receivable.competence,
                "due_date": receivable.due_date.isoformat(),
                "amount": str(receivable.balance),
                "status": receivable.status,
            },
            "charge": None
            if charge is None
            else {
                "type": charge.charge_type,
                "provider": charge.provider,
                "status": charge.status,
                "digitable_line": charge.digitable_line,
                "barcode": charge.barcode,
                "pix_copy_paste": charge.pix_copy_paste,
                "document_url": charge.document_url,
            },
        }
    )
