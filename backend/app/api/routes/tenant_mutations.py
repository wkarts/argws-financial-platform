from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_company_access, get_tenant_db, require_permission
from app.core.errors import APIError
from app.models.tenant import BankAccount, BankAgreement, Company, Contract, Customer, ServiceCatalog
from app.schemas.auth import AuthUser
from app.schemas.common import SuccessResponse
from app.schemas.tenant import CompanyRead, ContractRead, ServiceRead
from app.services.audit import tenant_audit

router = APIRouter(prefix="/api/v1", tags=["Cadastros - Edição"])


def digits(value: str | None) -> str | None:
    return "".join(ch for ch in value if ch.isdigit()) if value else value


class CompanyUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=2, max_length=200)
    trade_name: str | None = Field(default=None, max_length=160)
    tax_id: str | None = Field(default=None, min_length=11, max_length=20)
    state_registration: str | None = None
    municipal_registration: str | None = None
    tax_regime: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: dict[str, Any] | None = None
    branding: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("tax_id")
    @classmethod
    def normalize_tax_id(cls, value: str | None) -> str | None:
        return digits(value)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = None
    default_amount: Decimal | None = Field(default=None, ge=0)
    default_frequency: str | None = None
    fiscal_service_code: str | None = None
    is_active: bool | None = None


class ContractUpdate(BaseModel):
    customer_id: UUID | None = None
    service_id: UUID | None = None
    description: str | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    frequency: str | None = None
    interval_count: int | None = Field(default=None, ge=1, le=36)
    billing_method: str | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    start_date: date | None = None
    end_date: date | None = None
    issue_days_before_due: int | None = Field(default=None, ge=0, le=365)
    interest_percent_monthly: Decimal | None = Field(default=None, ge=0)
    fine_percent: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    fiscal_trigger: str | None = None
    status: str | None = None


class BankAccountUpdate(BaseModel):
    bank_code: str | None = Field(default=None, min_length=3, max_length=3)
    bank_name: str | None = None
    branch: str | None = None
    branch_digit: str | None = None
    account: str | None = None
    account_digit: str | None = None
    account_type: str | None = None
    pix_key_type: str | None = None
    pix_key: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class BankAgreementUpdate(BaseModel):
    bank_account_id: UUID | None = None
    name: str | None = None
    provider: str | None = None
    environment: str | None = None
    agreement_number: str | None = None
    wallet: str | None = None
    beneficiary_code: str | None = None
    cnab_layout: str | None = None
    is_active: bool | None = None


@router.patch("/companies/{company_id}", response_model=SuccessResponse[CompanyRead])
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    user: AuthUser = Depends(require_permission("companies.update")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[CompanyRead]:
    ensure_company_access(user, company_id)
    company = await session.get(Company, company_id)
    if company is None:
        raise APIError("COMPANY_NOT_FOUND", "Empresa não encontrada.", 404)
    values = payload.model_dump(exclude_unset=True)
    new_tax_id = values.get("tax_id")
    if new_tax_id and new_tax_id != company.tax_id:
        if await session.scalar(select(Company.id).where(Company.tax_id == new_tax_id, Company.id != company.id)):
            raise APIError("COMPANY_TAX_ID_EXISTS", "Já existe uma empresa com este CNPJ/CPF.", 409)
    before = CompanyRead.model_validate(company).model_dump(mode="json")
    for key, value in values.items():
        setattr(company, key, value)
    await tenant_audit(session, action="company.updated", entity_type="Company", entity_id=str(company.id), actor_id=user.id, company_id=str(company.id), before=before, after=values)
    await session.commit()
    await session.refresh(company)
    return SuccessResponse(data=CompanyRead.model_validate(company))


@router.patch("/services/{service_id}", response_model=SuccessResponse[ServiceRead])
async def update_service(
    service_id: UUID,
    payload: ServiceUpdate,
    user: AuthUser = Depends(require_permission("services.update")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[ServiceRead]:
    item = await session.get(ServiceCatalog, service_id)
    if item is None:
        raise APIError("SERVICE_NOT_FOUND", "Serviço não encontrado.", 404)
    values = payload.model_dump(exclude_unset=True)
    before = ServiceRead.model_validate(item).model_dump(mode="json")
    for key, value in values.items():
        setattr(item, key, value)
    await tenant_audit(session, action="service.updated", entity_type="Service", entity_id=str(item.id), actor_id=user.id, before=before, after=values)
    await session.commit()
    await session.refresh(item)
    return SuccessResponse(data=ServiceRead.model_validate(item))


@router.patch("/contracts/{contract_id}", response_model=SuccessResponse[ContractRead])
async def update_contract(
    contract_id: UUID,
    payload: ContractUpdate,
    user: AuthUser = Depends(require_permission("contracts.update")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[ContractRead]:
    item = await session.get(Contract, contract_id)
    if item is None:
        raise APIError("CONTRACT_NOT_FOUND", "Contrato não encontrado.", 404)
    ensure_company_access(user, item.company_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("customer_id") and await session.get(Customer, values["customer_id"]) is None:
        raise APIError("CUSTOMER_NOT_FOUND", "Cliente não encontrado.", 404)
    if values.get("service_id") and await session.get(ServiceCatalog, values["service_id"]) is None:
        raise APIError("SERVICE_NOT_FOUND", "Serviço não encontrado.", 404)
    before = ContractRead.model_validate(item).model_dump(mode="json")
    for key, value in values.items():
        setattr(item, key, value)
    await tenant_audit(session, action="contract.updated", entity_type="Contract", entity_id=str(item.id), actor_id=user.id, company_id=str(item.company_id), before=before, after=values)
    await session.commit()
    await session.refresh(item)
    return SuccessResponse(data=ContractRead.model_validate(item))


@router.patch("/bank-accounts/{account_id}", response_model=SuccessResponse[dict])
async def update_bank_account(
    account_id: UUID,
    payload: BankAccountUpdate,
    user: AuthUser = Depends(require_permission("banking.manage")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    item = await session.get(BankAccount, account_id)
    if item is None:
        raise APIError("BANK_ACCOUNT_NOT_FOUND", "Conta bancária não encontrada.", 404)
    ensure_company_access(user, item.company_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("is_default"):
        for current in (await session.execute(select(BankAccount).where(BankAccount.company_id == item.company_id, BankAccount.id != item.id, BankAccount.is_default.is_(True)))).scalars():
            current.is_default = False
    for key, value in values.items():
        setattr(item, key, value)
    await tenant_audit(session, action="bank_account.updated", entity_type="BankAccount", entity_id=str(item.id), actor_id=user.id, company_id=str(item.company_id), after={"bank_code": item.bank_code, "is_default": item.is_default, "is_active": item.is_active})
    await session.commit()
    return SuccessResponse(data={"id": str(item.id), "bank_code": item.bank_code, "bank_name": item.bank_name, "is_active": item.is_active})


@router.patch("/bank-agreements/{agreement_id}", response_model=SuccessResponse[dict])
async def update_bank_agreement(
    agreement_id: UUID,
    payload: BankAgreementUpdate,
    user: AuthUser = Depends(require_permission("banking.manage")),
    session: AsyncSession = Depends(get_tenant_db),
) -> SuccessResponse[dict]:
    item = await session.get(BankAgreement, agreement_id)
    if item is None:
        raise APIError("BANK_AGREEMENT_NOT_FOUND", "Convênio bancário não encontrado.", 404)
    ensure_company_access(user, item.company_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("bank_account_id"):
        account = await session.get(BankAccount, values["bank_account_id"])
        if account is None or account.company_id != item.company_id:
            raise APIError("BANK_ACCOUNT_NOT_FOUND", "Conta bancária não encontrada para esta empresa.", 404)
    for key, value in values.items():
        setattr(item, key, value)
    await tenant_audit(session, action="bank_agreement.updated", entity_type="BankAgreement", entity_id=str(item.id), actor_id=user.id, company_id=str(item.company_id), after={"provider": item.provider, "environment": item.environment, "cnab_layout": item.cnab_layout, "is_active": item.is_active})
    await session.commit()
    return SuccessResponse(data={"id": str(item.id), "name": item.name, "is_active": item.is_active})
