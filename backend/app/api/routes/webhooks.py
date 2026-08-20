from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_context_dep, get_tenant_db
from app.core.config import settings
from app.core.errors import APIError
from app.core.tenant_context import TenantContext
from app.core.webhook_security import validate_webhook_timestamp
from app.models.tenant import Charge, IntegrationSetting, Notification, WebhookEvent
from app.services.billing import BillingService
from app.core.secrets import secret_cipher

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


def payload_event_id(provider: str, payload: dict[str, Any], raw: bytes) -> str:
    return str(
        payload.get("event_id")
        or payload.get("id")
        or payload.get("key", {}).get("id")
        or payload.get("data", {}).get("key", {}).get("id")
        or f"{provider}-{hashlib.sha256(raw).hexdigest()}"
    )[:180]


async def persist_webhook(
    session: AsyncSession,
    *,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
    raw: bytes,
    signature_valid: bool,
) -> tuple[WebhookEvent, bool]:
    item_id = uuid4()
    statement = (
        pg_insert(WebhookEvent)
        .values(
            id=item_id,
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            signature_valid=signature_valid,
            payload_hash=hashlib.sha256(raw).hexdigest(),
            payload=payload,
            status="RECEIVED",
            received_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(constraint="uq_webhook_provider_event")
        .returning(WebhookEvent.id)
    )
    inserted_id = await session.scalar(statement)
    if inserted_id is None:
        existing = await session.scalar(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider, WebhookEvent.event_id == event_id
            )
        )
        if existing is None:
            raise APIError(
                "WEBHOOK_IDEMPOTENCY_CONFLICT",
                "Não foi possível recuperar o evento idempotente.",
                409,
            )
        return existing, False
    item = await session.get(WebhookEvent, inserted_id)
    if item is None:
        raise APIError("WEBHOOK_PERSISTENCE_FAILED", "Falha ao persistir webhook.", 500)
    return item, True


async def configured_webhook_secrets(session: AsyncSession, providers: list[str], global_secret: str = "") -> list[str]:
    values = [global_secret] if global_secret else []
    items = list((await session.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.provider.in_([item.upper() for item in providers]),
            IntegrationSetting.is_enabled.is_(True),
        )
    )).scalars())
    for item in items:
        if not item.encrypted_secrets:
            continue
        try:
            data = json.loads(secret_cipher.decrypt(item.encrypted_secrets))
            value = str(data.get("webhook_secret") or "")
            if value:
                values.append(value)
        except Exception:
            continue
    return values


def valid_shared_secret(provided: str, expected: list[str]) -> bool:
    return bool(provided and any(hmac.compare_digest(provided, value) for value in expected if value))


@router.post("/evolution", response_model=dict)
async def evolution_webhook(
    request: Request,
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
    x_webhook_secret: str = Header(default=""),
    x_webhook_timestamp: str = Header(default=""),
) -> dict:
    try:
        validate_webhook_timestamp(
            x_webhook_timestamp, max_age_seconds=settings.webhook_max_age_seconds
        )
    except ValueError as exc:
        raise APIError("STALE_WEBHOOK", "Timestamp do webhook inválido ou expirado.", 401) from exc
    raw = await request.body()
    try:
        payload: dict[str, Any] = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise APIError("INVALID_WEBHOOK_JSON", "Payload JSON inválido.", 400) from exc
    expected = await configured_webhook_secrets(session, ["EVOLUTION"], settings.evolution_webhook_secret)
    signature_valid = valid_shared_secret(x_webhook_secret, expected)
    if not expected and settings.app_env == "production":
        raise APIError("WEBHOOK_SECRET_NOT_CONFIGURED", "Webhook Evolution sem segredo configurado.", 503)
    if expected and not signature_valid:
        raise APIError("INVALID_WEBHOOK_SIGNATURE", "Assinatura do webhook inválida.", 401)
    event_type = str(payload.get("event") or payload.get("type") or "UNKNOWN").upper()
    event_id = payload_event_id("EVOLUTION", payload, raw)
    event, created = await persist_webhook(
        session,
        provider="EVOLUTION",
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        raw=raw,
        signature_valid=signature_valid or not bool(expected),
    )
    if not created:
        return {"success": True, "idempotent": True, "event_id": event_id}
    message_id = (
        payload.get("data", {}).get("key", {}).get("id")
        or payload.get("key", {}).get("id")
        or payload.get("messageId")
    )
    status_map = {
        "MESSAGES.UPDATE": "DELIVERED",
        "SEND_MESSAGE": "SENT",
        "MESSAGE.DELIVERED": "DELIVERED",
        "MESSAGE.READ": "READ",
        "MESSAGES_UPSERT": "DELIVERED",
    }
    if message_id:
        notification = await session.scalar(select(Notification).where(Notification.external_id == str(message_id)))
        if notification:
            notification.status = status_map.get(event_type, notification.status)
            now = datetime.now(UTC)
            if notification.status == "DELIVERED":
                notification.delivered_at = now
            elif notification.status == "READ":
                notification.read_at = now
    event.status = "PROCESSED"
    event.processed_at = datetime.now(UTC)
    await session.commit()
    return {"success": True, "event_id": event_id, "tenant_id": context.tenant_id}


@router.post("/banking/{provider}", response_model=dict)
async def banking_webhook(
    provider: str,
    request: Request,
    context: TenantContext = Depends(get_tenant_context_dep),
    session: AsyncSession = Depends(get_tenant_db),
    x_webhook_secret: str = Header(default=""),
    x_webhook_timestamp: str = Header(default=""),
) -> dict:
    try:
        validate_webhook_timestamp(
            x_webhook_timestamp, max_age_seconds=settings.webhook_max_age_seconds
        )
    except ValueError as exc:
        raise APIError("STALE_WEBHOOK", "Timestamp do webhook inválido ou expirado.", 401) from exc
    raw = await request.body()
    try:
        payload: dict[str, Any] = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise APIError("INVALID_WEBHOOK_JSON", "Payload JSON inválido.", 400) from exc
    # Adapters reais podem substituir esta validação por mTLS/JWS/HMAC conforme o banco.
    # O endpoint genérico nunca aceita segredo vindo do próprio payload.
    provider_name = provider.upper()
    expected = await configured_webhook_secrets(
        session, [provider_name, f"BANKING_{provider_name}"], settings.banking_webhook_secret
    )
    if not expected and settings.app_env == "production":
        raise APIError("WEBHOOK_SECRET_NOT_CONFIGURED", "Webhook bancário sem segredo configurado.", 503)
    if expected and not valid_shared_secret(x_webhook_secret, expected):
        raise APIError("INVALID_WEBHOOK_SIGNATURE", "Assinatura do webhook inválida.", 401)
    event_id = payload_event_id(provider.upper(), payload, raw)
    event_type = str(payload.get("event") or payload.get("type") or "PAYMENT").upper()
    event, created = await persist_webhook(
        session,
        provider=provider.upper(),
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        raw=raw,
        signature_valid=True,
    )
    if not created:
        return {"success": True, "idempotent": True, "event_id": event_id}
    if event_type in {"PAYMENT", "PAID", "CHARGE.PAID", "PIX_RECEIVED"}:
        receivable_id = payload.get("receivable_id")
        charge_external_id = payload.get("charge_external_id") or payload.get("external_charge_id")
        charge = None
        if charge_external_id:
            charge = await session.scalar(
                select(Charge).where(Charge.provider == provider.upper(), Charge.external_id == str(charge_external_id))
            )
            if charge:
                receivable_id = str(charge.receivable_id)
        if not receivable_id:
            raise APIError("WEBHOOK_RECEIVABLE_NOT_RESOLVED", "Não foi possível identificar o recebível.", 422)
        await BillingService(session).register_payment(
            receivable_id=str(receivable_id),
            charge_id=str(charge.id) if charge else None,
            provider=provider.upper(),
            external_id=str(payload.get("payment_id") or event_id),
            end_to_end_id=payload.get("end_to_end_id") or payload.get("endToEndId"),
            amount=Decimal(str(payload["amount"])),
            paid_at=datetime.fromisoformat(str(payload.get("paid_at") or datetime.now(UTC).isoformat())),
            payment_method=str(payload.get("payment_method") or "PIX"),
            raw_payload=payload,
        )
    event.status = "PROCESSED"
    event.processed_at = datetime.now(UTC)
    await session.commit()
    return {"success": True, "event_id": event_id, "tenant_id": context.tenant_id}
