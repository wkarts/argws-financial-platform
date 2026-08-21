from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PlatformBase, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    legal_document: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROVISIONING", index=True)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False, default="ENTERPRISE")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Bahia")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="pt-BR")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    limits: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    domains: Mapped[list[TenantDomain]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    database: Mapped[TenantDatabase | None] = relationship(
        back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )
    storage: Mapped[TenantStorage | None] = relationship(
        back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )
    provisioning_jobs: Mapped[list[ProvisioningJob]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class TenantDomain(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "tenant_domains"
    __table_args__ = (
        UniqueConstraint("hostname", name="uq_tenant_domains_hostname"),
        Index("ix_tenant_domains_tenant_primary", "tenant_id", "is_primary"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    hostname: Mapped[str] = mapped_column(String(253), nullable=False)
    domain_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PROVISIONED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redirect_to_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(128))
    dns_record_id: Mapped[str | None] = mapped_column(String(128))
    dns_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ssl_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    ssl_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped[Tenant] = relationship(back_populates="domains")


class TenantDatabase(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "tenant_databases"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_databases_tenant"),
        UniqueConstraint("database_name", name="uq_tenant_databases_database_name"),
        UniqueConstraint("database_user", name="uq_tenant_databases_database_user"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    database_name: Mapped[str] = mapped_column(String(63), nullable=False)
    database_user: Mapped[str] = mapped_column(String(63), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    credential_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    migrated_revision: Mapped[str | None] = mapped_column(String(64))
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped[Tenant] = relationship(back_populates="database")


class TenantStorage(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "tenant_storage"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_storage_tenant"),
        UniqueConstraint("bucket", name="uq_tenant_storage_bucket"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="S3")
    bucket: Mapped[str] = mapped_column(String(63), nullable=False)
    prefix: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped[Tenant] = relationship(back_populates="storage")


class PlatformUser(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "platform_users"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="PLATFORM_ADMIN")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProvisioningJob(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "provisioning_jobs"
    __table_args__ = (Index("ix_provisioning_jobs_tenant_status", "tenant_id", "status"),)

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="PROVISION")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    current_step: Mapped[str] = mapped_column(String(80), nullable=False, default="CREATED")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped[Tenant] = relationship(back_populates="provisioning_jobs")

    def add_event(self, step: str, message: str, level: str = "INFO") -> None:
        current = list(self.events or [])
        current.append(
            {
                "at": datetime.now(UTC).isoformat(),
                "step": step,
                "level": level,
                "message": message,
            }
        )
        self.events = current[-300:]


class PlatformRefreshToken(UUIDPrimaryKeyMixin, PlatformBase):
    __tablename__ = "platform_refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PlatformAuditLog(UUIDPrimaryKeyMixin, PlatformBase):
    __tablename__ = "platform_audit_logs"
    __table_args__ = (Index("ix_platform_audit_entity", "entity_type", "entity_id"),)

    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    tenant_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BackupRun(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "backup_runs"

    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="FULL")
    tenant_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    path: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    destinations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class PlatformPlan(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    """Plano comercial e técnico aplicado aos tenants."""

    __tablename__ = "platform_plans"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    limits: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PlatformSetting(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="GENERAL", index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)


class PlatformIntegration(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "platform_integrations"

    provider: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    encrypted_secrets: Mapped[str] = mapped_column(Text, nullable=False, default="")
    health_status: Mapped[str | None] = mapped_column(String(32))
    health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class TenantUsageSnapshot(UUIDPrimaryKeyMixin, PlatformBase):
    __tablename__ = "tenant_usage_snapshots"
    __table_args__ = (Index("ix_usage_tenant_period", "tenant_id", "period"),)

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SupportSession(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "support_sessions"
    __table_args__ = (Index("ix_support_tenant_status", "tenant_id", "status"),)

    platform_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RestoreRun(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "restore_runs"

    backup_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("backup_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="FULL")
    tenant_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    requested_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class PlatformApiKey(UUIDPrimaryKeyMixin, TimestampMixin, PlatformBase):
    __tablename__ = "platform_api_keys"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_ips: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
