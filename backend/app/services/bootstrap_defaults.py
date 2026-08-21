from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import PlatformPlan, PlatformSetting
from app.models.tenant import TenantRole

# Permissões efetivamente consumidas pelas APIs. A lista também é usada na UI
# para montar perfis sem depender de strings espalhadas pelo frontend.
ALL_TENANT_PERMISSIONS: list[str] = [
    "dashboard.read",
    "companies.read", "companies.create", "companies.update", "companies.deactivate",
    "customers.read", "customers.create", "customers.update", "customers.deactivate",
    "contacts.read", "contacts.create", "contacts.update", "contacts.delete",
    "services.read", "services.create", "services.update", "services.deactivate",
    "contracts.read", "contracts.create", "contracts.update", "contracts.action",
    "recurrences.generate",
    "receivables.read", "receivables.create", "receivables.update", "receivables.action",
    "charges.read", "charges.create", "charges.action",
    "pix_automatic.read", "pix_automatic.manage",
    "pix_automatic.read", "pix_automatic.manage",
    "payments.read", "payments.create", "payments.reverse",
    "banking.read", "banking.manage", "bank_statements.read", "bank_statements.import",
    "cnab.generate", "cnab.import", "cnab.read",
    "reconciliation.read", "reconciliation.manage",
    "negotiations.read", "negotiations.create", "negotiations.approve", "negotiations.cancel",
    "fiscal.read", "fiscal.create", "fiscal.action",
    "receipts.read", "receipts.create",
    "notifications.read", "notifications.manage",
    "integrations.read", "integrations.manage",
    "webhooks.read", "webhooks.manage",
    "api_keys.read", "api_keys.manage",
    "documents.read", "documents.manage",
    "imports.read", "imports.manage",
    "exports.read", "exports.create",
    "reports.view",
    "payment_links.read", "payment_links.manage",
    "users.read", "users.manage", "roles.read", "roles.manage",
    "audit.read",
]

DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "code": "STARTER", "name": "Starter", "description": "Operação essencial para uma empresa.",
        "monthly_price": Decimal("97.00"), "annual_price": Decimal("970.00"), "sort_order": 10,
        "features": {"boleto": True, "pix": True, "pix_automatic": False, "cnab": False, "whatsapp": False, "nfse": False, "custom_domain": False},
        "limits": {"companies": 1, "users": 3, "customers": 500, "monthly_charges": 500, "storage_gb": 5},
    },
    {
        "code": "PROFESSIONAL", "name": "Professional", "description": "Cobrança automatizada, CNAB e comunicação.",
        "monthly_price": Decimal("197.00"), "annual_price": Decimal("1970.00"), "sort_order": 20,
        "features": {"boleto": True, "pix": True, "pix_automatic": True, "cnab": True, "whatsapp": True, "nfse": True, "custom_domain": True},
        "limits": {"companies": 3, "users": 10, "customers": 5000, "monthly_charges": 5000, "storage_gb": 25},
    },
    {
        "code": "BUSINESS", "name": "Business", "description": "Múltiplas empresas, integrações e automação ampliada.",
        "monthly_price": Decimal("397.00"), "annual_price": Decimal("3970.00"), "sort_order": 30,
        "features": {"boleto": True, "pix": True, "pix_automatic": True, "cnab": True, "whatsapp": True, "nfse": True, "custom_domain": True, "api": True, "webhooks": True},
        "limits": {"companies": 10, "users": 50, "customers": 50000, "monthly_charges": 50000, "storage_gb": 100},
    },
    {
        "code": "ENTERPRISE", "name": "Enterprise", "description": "Capacidade negociada, suporte e governança avançada.",
        "monthly_price": Decimal("0.00"), "annual_price": Decimal("0.00"), "sort_order": 40, "is_public": False,
        "features": {"boleto": True, "pix": True, "pix_automatic": True, "cnab": True, "whatsapp": True, "nfse": True, "custom_domain": True, "api": True, "webhooks": True, "support_impersonation": True},
        "limits": {"companies": 0, "users": 0, "customers": 0, "monthly_charges": 0, "storage_gb": 0},
    },
]

DEFAULT_PLATFORM_SETTINGS: list[dict[str, Any]] = [
    {"key": "platform.locale", "category": "GENERAL", "value": {"language": "pt-BR", "currency": "BRL", "timezone": "America/Bahia"}, "description": "Localização padrão."},
    {"key": "tenant.provisioning", "category": "PROVISIONING", "value": {"temporary_domain": True, "custom_domains": True, "database_per_tenant": True, "storage_per_tenant": True}, "description": "Política de provisionamento."},
    {"key": "backup.retention", "category": "BACKUP", "value": {"daily": 14, "weekly": 8, "monthly": 12, "yearly": 5}, "description": "Retenção padrão de backups."},
    {"key": "security.support_session", "category": "SECURITY", "value": {"max_minutes": 120, "reason_required": True, "audit_required": True}, "description": "Política de acesso assistido."},
    {"key": "financial.default_rules", "category": "FINANCIAL", "value": {"currency": "BRL", "late_fee_percent": 2, "monthly_interest_percent": 1}, "description": "Regras financeiras iniciais."},
]

ROLE_DEFINITIONS: list[dict[str, Any]] = [
    {"code": "TENANT_ADMIN", "name": "Administrador", "description": "Acesso integral ao tenant.", "permissions": ["*"], "is_system": True},
    {"code": "FINANCE_MANAGER", "name": "Gestor financeiro", "description": "Gestão completa do ciclo financeiro.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p not in {"users.manage", "roles.manage", "integrations.manage", "api_keys.manage"}], "is_system": True},
    {"code": "FINANCE_OPERATOR", "name": "Operador financeiro", "description": "Operação diária de clientes, contratos, cobranças e conciliação.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.split(".", 1)[0] in {"dashboard", "customers", "contacts", "services", "contracts", "receivables", "charges", "pix_automatic", "payments", "banking", "bank_statements", "cnab", "reconciliation", "negotiations", "documents", "exports", "reports", "payment_links"} and not p.endswith("deactivate")], "is_system": True},
    {"code": "COLLECTION_OPERATOR", "name": "Operador de cobrança", "description": "Cobranças, régua e comunicação.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.split(".", 1)[0] in {"dashboard", "customers", "contacts", "receivables", "charges", "pix_automatic", "payments", "notifications", "payment_links", "documents"}], "is_system": True},
    {"code": "TREASURY", "name": "Tesouraria", "description": "Bancos, pagamentos, CNAB e conciliação.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.split(".", 1)[0] in {"dashboard", "receivables", "charges", "pix_automatic", "payments", "banking", "bank_statements", "cnab", "reconciliation", "documents", "reports"}], "is_system": True},
    {"code": "FISCAL", "name": "Fiscal", "description": "Documentos fiscais e recibos.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.split(".", 1)[0] in {"dashboard", "customers", "receivables", "payments", "fiscal", "receipts", "documents", "exports", "reports"}], "is_system": True},
    {"code": "AUDITOR", "name": "Auditor", "description": "Consulta e auditoria sem alterações financeiras.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.endswith(".read") or p == "reports.view"], "is_system": True},
    {"code": "VIEWER", "name": "Consulta", "description": "Acesso estritamente de leitura.", "permissions": [p for p in ALL_TENANT_PERMISSIONS if p.endswith(".read")], "is_system": True},
]


async def ensure_platform_defaults(session: AsyncSession) -> None:
    for definition in DEFAULT_PLANS:
        code = definition["code"]
        item = await session.scalar(select(PlatformPlan).where(PlatformPlan.code == code))
        if item is None:
            session.add(PlatformPlan(**definition))
    for definition in DEFAULT_PLATFORM_SETTINGS:
        item = await session.scalar(select(PlatformSetting).where(PlatformSetting.key == definition["key"]))
        if item is None:
            session.add(PlatformSetting(**definition))
    await session.flush()


async def ensure_tenant_roles(session: AsyncSession) -> None:
    for definition in ROLE_DEFINITIONS:
        item = await session.scalar(select(TenantRole).where(TenantRole.code == definition["code"]))
        if item is None:
            session.add(TenantRole(**definition))
        elif item.is_system:
            # Perfis de sistema acompanham a versão da plataforma; perfis customizados não são tocados.
            item.name = definition["name"]
            item.description = definition["description"]
            item.permissions = definition["permissions"]
            item.is_active = True
    await session.flush()
