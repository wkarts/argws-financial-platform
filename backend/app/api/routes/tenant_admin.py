from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_tenant_db, require_permission
from app.core.errors import APIError
from app.core.security import hash_password
from app.models.tenant import Company, TenantRefreshToken, TenantUser, UserCompany
from app.schemas.auth import AuthUser
from app.schemas.common import SuccessResponse
from app.schemas.tenant import PasswordResetInput, TenantUserCreate, TenantUserUpdate
from app.services.audit import tenant_audit

router = APIRouter(prefix="/api/v1", tags=["Tenant - Administração"])

ROLE_PRESETS: dict[str, list[str]] = {
    "TENANT_ADMIN": ["*"],
    "FINANCE_MANAGER": [
        "companies.read", "customers.read", "customers.create", "customers.update",
        "services.read", "services.create", "contracts.read", "contracts.create",
        "receivables.read", "receivables.create", "charges.read", "charges.create",
        "payments.read", "payments.create", "banking.read", "banking.manage",
        "reconciliation.read", "reconciliation.manage", "notifications.read",
        "notifications.manage", "integrations.read", "receipts.read", "receipts.create",
        "fiscal.read", "fiscal.create", "documents.read", "audit.read",
    ],
    "FINANCE_OPERATOR": [
        "companies.read", "customers.read", "customers.create", "customers.update",
        "services.read", "contracts.read", "receivables.read", "receivables.create",
        "charges.read", "charges.create", "payments.read", "payments.create",
        "banking.read", "reconciliation.read", "notifications.read", "receipts.read",
        "receipts.create", "fiscal.read", "documents.read",
    ],
    "COLLECTION_OPERATOR": [
        "companies.read", "customers.read", "contracts.read", "receivables.read",
        "charges.read", "charges.create", "notifications.read", "notifications.manage",
    ],
    "TREASURY": [
        "companies.read", "receivables.read", "charges.read", "payments.read",
        "payments.create", "banking.read", "banking.manage", "reconciliation.read",
        "reconciliation.manage", "documents.read",
    ],
    "FISCAL": [
        "companies.read", "customers.read", "receivables.read", "payments.read",
        "fiscal.read", "fiscal.create", "receipts.read", "documents.read",
    ],
    "AUDITOR": [
        "companies.read", "customers.read", "services.read", "contracts.read",
        "receivables.read", "charges.read", "payments.read", "banking.read",
        "reconciliation.read", "notifications.read", "fiscal.read", "receipts.read",
        "documents.read", "audit.read", "integrations.read",
    ],
    "VIEWER": [
        "companies.read", "customers.read", "services.read", "contracts.read",
        "receivables.read", "charges.read", "payments.read", "banking.read",
        "reconciliation.read", "fiscal.read", "receipts.read", "documents.read",
    ],
}


def serialize_user(item: TenantUser) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "email": item.email,
        "phone": item.phone,
        "role": item.role,
        "permissions": item.permissions,
        "companies": [str(link.company_id) for link in item.companies],
        "is_active": item.is_active,
        "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None,
        "created_at": item.created_at.isoformat(),
    }


async def validate_companies(session: AsyncSession, company_ids: list[UUID]) -> None:
    if not company_ids:
        return
    count = len(set(company_ids))
    found = len(list((await session.scalars(select(Company.id).where(Company.id.in_(company_ids)))).all()))
    if found != count:
        raise APIError("COMPANY_NOT_FOUND", "Uma ou mais empresas informadas não existem.", 404)


@router.get("/role-presets", response_model=SuccessResponse[dict])
async def role_presets(
    _: AuthUser = Depends(require_permission("users.read")),
) -> SuccessResponse[dict]:
    return SuccessResponse(data=ROLE_PRESETS)


@router.get("/users", response_model=SuccessResponse[list[dict]])
async def list_users(
    _: AuthUser = Depends(require_permission("users.read")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[list[dict]]:
    items = list((await session.execute(
        select(TenantUser).options(selectinload(TenantUser.companies)).order_by(TenantUser.name)
    )).scalars())
    return SuccessResponse(data=[serialize_user(item) for item in items])


@router.post("/users", response_model=SuccessResponse[dict], status_code=201)
async def create_user(
    payload: TenantUserCreate,
    actor: AuthUser = Depends(require_permission("users.manage")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    email = str(payload.email).lower()
    if await session.scalar(select(TenantUser.id).where(TenantUser.email == email)):
        raise APIError("USER_EMAIL_EXISTS", "E-mail já cadastrado neste tenant.", 409)
    await validate_companies(session, payload.company_ids)
    role = payload.role.upper()
    permissions = payload.permissions or ROLE_PRESETS.get(role, [])
    item = TenantUser(
        name=payload.name,
        email=email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=role,
        permissions=permissions,
        is_active=payload.is_active,
    )
    session.add(item)
    await session.flush()
    for index, company_id in enumerate(dict.fromkeys(payload.company_ids)):
        session.add(UserCompany(user_id=item.id, company_id=company_id, is_default=index == 0))
    await tenant_audit(
        session,
        action="user.created",
        entity_type="TenantUser",
        entity_id=str(item.id),
        actor_id=actor.id,
        after={"name": item.name, "email": item.email, "role": item.role, "companies": [str(v) for v in payload.company_ids]},
    )
    await session.commit()
    item = await session.scalar(select(TenantUser).where(TenantUser.id == item.id).options(selectinload(TenantUser.companies)))
    assert item is not None
    return SuccessResponse(data=serialize_user(item))


@router.patch("/users/{user_id}", response_model=SuccessResponse[dict])
async def update_user(
    user_id: UUID,
    payload: TenantUserUpdate,
    actor: AuthUser = Depends(require_permission("users.manage")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    item = await session.scalar(select(TenantUser).where(TenantUser.id == user_id).options(selectinload(TenantUser.companies)))
    if item is None:
        raise APIError("USER_NOT_FOUND", "Usuário não encontrado.", 404)
    if str(item.id) == actor.id and payload.is_active is False:
        raise APIError("CANNOT_DISABLE_SELF", "O usuário não pode desativar a própria conta.", 409)
    before = serialize_user(item)
    values = payload.model_dump(exclude_unset=True, exclude={"company_ids"})
    if "role" in values and values["role"]:
        values["role"] = values["role"].upper()
        if payload.permissions is None:
            values["permissions"] = ROLE_PRESETS.get(values["role"], item.permissions)
    for key, value in values.items():
        setattr(item, key, value)
    if payload.company_ids is not None:
        await validate_companies(session, payload.company_ids)
        await session.execute(delete(UserCompany).where(UserCompany.user_id == item.id))
        for index, company_id in enumerate(dict.fromkeys(payload.company_ids)):
            session.add(UserCompany(user_id=item.id, company_id=company_id, is_default=index == 0))
    await session.flush()
    await tenant_audit(
        session,
        action="user.updated",
        entity_type="TenantUser",
        entity_id=str(item.id),
        actor_id=actor.id,
        before=before,
        after=payload.model_dump(mode="json", exclude_unset=True),
    )
    await session.commit()
    item = await session.scalar(select(TenantUser).where(TenantUser.id == user_id).options(selectinload(TenantUser.companies)))
    assert item is not None
    return SuccessResponse(data=serialize_user(item))


@router.post("/users/{user_id}/password", response_model=SuccessResponse[dict])
async def reset_user_password(
    user_id: UUID,
    payload: PasswordResetInput,
    actor: AuthUser = Depends(require_permission("users.manage")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    item = await session.get(TenantUser, user_id)
    if item is None:
        raise APIError("USER_NOT_FOUND", "Usuário não encontrado.", 404)
    item.password_hash = hash_password(payload.password)
    item.failed_login_attempts = 0
    item.locked_until = None
    await session.execute(
        delete(TenantRefreshToken).where(TenantRefreshToken.user_id == item.id, TenantRefreshToken.revoked_at.is_(None))
    )
    await tenant_audit(
        session,
        action="user.password_reset",
        entity_type="TenantUser",
        entity_id=str(item.id),
        actor_id=actor.id,
    )
    await session.commit()
    return SuccessResponse(data={"id": str(item.id), "password_reset": True})
