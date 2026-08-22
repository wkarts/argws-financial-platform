from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import settings
from app.main import allowed_hosts
from app.models.platform import TenantDomain
from app.providers.cloudflare import DNSRecordResult
from app.services.provisioning import ProvisioningService


def test_internal_api_hostname_is_trusted_for_prometheus() -> None:
    assert "financial-api" in allowed_hosts


@pytest.mark.asyncio
async def test_provisioned_domain_reconciles_wildcard_before_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "cloudflare_enabled", True)
    monkeypatch.setattr(settings, "cloudflare_provisioning_mode", "wildcard")
    monkeypatch.setattr(settings, "cloudflare_api_token", "test-token")
    monkeypatch.setattr(settings, "cloudflare_zone_id", "test-zone")
    monkeypatch.setattr(settings, "public_scheme", "https")

    service = ProvisioningService()

    async def fake_wildcard() -> DNSRecordResult:
        return DNSRecordResult(
            record_id="wildcard-id",
            name="*.finance.argws.com.br",
            content="proxy.finance.argws.com.br",
            proxied=False,
        )

    monkeypatch.setattr(service.cloudflare, "ensure_managed_wildcard", fake_wildcard)
    domain = TenantDomain(
        tenant_id=uuid4(),
        hostname="cliente.finance.argws.com.br",
        domain_type="PROVISIONED",
        status="PENDING",
        is_primary=True,
        is_temporary=True,
    )

    detail = await service._activate_provisioned_domain(domain)

    assert "*.finance.argws.com.br" in detail
    assert domain.status == "ACTIVE"
    assert domain.dns_verified_at is not None
    assert domain.last_checked_at is not None
    assert domain.ssl_status == "ACTIVE"
    assert domain.last_error is None


def test_cloudpanel_agent_can_create_reverse_proxy() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "infrastructure" / "cloudpanel-agent" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "clpctl site:add:reverse-proxy" in script
    assert "CLOUDPANEL_SITE_USER_PASSWORD" in script
    assert "GATEWAY_PORT:-18800" in script


def test_public_landing_has_canonical_actions_and_mobile_viewport() -> None:
    root = Path(__file__).resolve().parents[2]
    landing = (root / "infrastructure" / "docker" / "gateway" / "landing" / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in landing
    assert "https://demo.finance.argws.com.br/" in landing
    assert "https://control.finance.argws.com.br/" in landing
    assert "ARGWS Financial Platform" in landing
