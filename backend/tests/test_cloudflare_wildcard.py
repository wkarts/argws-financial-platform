from __future__ import annotations

import pytest

from app.core.config import settings
from app.providers.cloudflare import CloudflareDNSProvider, DNSRecordResult


@pytest.mark.asyncio
async def test_managed_wildcard_derives_dns_only_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "platform_domain", "financeiro.example.com")
    monkeypatch.setattr(settings, "tenant_domain_root", "financeiro.example.com")
    monkeypatch.setattr(settings, "cloudflare_tenant_record_target", "proxy.financeiro.example.com")

    provider = CloudflareDNSProvider()
    calls: list[tuple[str, str, str, bool | None]] = []

    async def fake_list_records(hostname: str, record_type: str | None = None):
        assert hostname == "financeiro.example.com"
        assert record_type is None
        return [{"id": "base", "type": "A", "name": hostname, "content": "203.0.113.10", "proxied": True}]

    async def fake_upsert_record(
        hostname: str,
        content: str,
        *,
        record_type: str = "CNAME",
        proxied: bool | None = None,
    ) -> DNSRecordResult:
        calls.append((hostname, content, record_type, proxied))
        return DNSRecordResult("id", hostname, content, bool(proxied), record_type)

    monkeypatch.setattr(provider, "list_records", fake_list_records)
    monkeypatch.setattr(provider, "upsert_record", fake_upsert_record)

    result = await provider.ensure_managed_wildcard()

    assert calls == [
        ("proxy.financeiro.example.com", "203.0.113.10", "A", False),
        ("*.financeiro.example.com", "proxy.financeiro.example.com", "CNAME", False),
    ]
    assert result.name == "*.financeiro.example.com"
    assert result.proxied is False
