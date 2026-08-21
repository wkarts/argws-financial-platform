from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from slugify import slugify

from app.schemas.common import ORMModel


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    legal_document: str | None = Field(default=None, max_length=32)
    timezone: str = "America/Bahia"
    plan_code: str = "ENTERPRISE"
    admin_name: str = Field(min_length=2, max_length=160)
    admin_email: str
    admin_password: str = Field(min_length=12, max_length=512)
    initial_company_name: str = Field(min_length=2, max_length=200)
    initial_company_tax_id: str = Field(min_length=11, max_length=20)
    features: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        return slugify(value) if value else None


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    status: str | None = None
    plan_code: str | None = None
    features: dict[str, Any] | None = None
    limits: dict[str, Any] | None = None
    suspended_reason: str | None = None


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=3, max_length=253)
    is_primary: bool = False

    @field_validator("hostname")
    @classmethod
    def normalize_hostname(cls, value: str) -> str:
        return value.lower().strip().rstrip(".")


class DomainRead(ORMModel):
    id: UUID
    hostname: str
    domain_type: str
    status: str
    is_primary: bool
    is_temporary: bool
    dns_verified_at: datetime | None
    ssl_status: str
    last_error: str | None


class TenantRead(ORMModel):
    id: UUID
    name: str
    slug: str
    legal_document: str | None
    status: str
    plan_code: str
    timezone: str
    features: dict[str, Any]
    limits: dict[str, Any]
    created_at: datetime
    domains: list[DomainRead] = Field(default_factory=list)


class ProvisioningJobRead(ORMModel):
    id: UUID
    tenant_id: UUID
    operation: str
    status: str
    current_step: str
    progress: int
    attempts: int
    correlation_id: str
    events: list[dict[str, Any]]
    started_at: datetime | None
    finished_at: datetime | None
    last_error: str | None
