from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import APIError


@dataclass(frozen=True, slots=True)
class DNSRecordResult:
    record_id: str
    name: str
    content: str
    proxied: bool


class CloudflareDNSProvider:
    base_url = "https://api.cloudflare.com/client/v4"

    def __init__(self) -> None:
        self.enabled = settings.cloudflare_enabled
        self.zone_id = settings.cloudflare_zone_id
        self.token = settings.cloudflare_api_token

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.zone_id and self.token)

    async def upsert_cname(self, hostname: str, target: str, proxied: bool | None = None) -> DNSRecordResult:
        if not self.configured:
            raise APIError("CLOUDFLARE_NOT_CONFIGURED", "Cloudflare não está configurado.", 503)
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        proxied_value = settings.cloudflare_proxied if proxied is None else proxied
        async with httpx.AsyncClient(timeout=30) as client:
            lookup = await client.get(
                f"{self.base_url}/zones/{self.zone_id}/dns_records",
                headers=headers,
                params={"type": "CNAME", "name": hostname},
            )
            lookup.raise_for_status()
            records = lookup.json().get("result", [])
            payload = {"type": "CNAME", "name": hostname, "content": target, "proxied": proxied_value, "ttl": 1}
            if records:
                record_id = records[0]["id"]
                response = await client.put(
                    f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}",
                    headers=headers,
                    json=payload,
                )
            else:
                response = await client.post(
                    f"{self.base_url}/zones/{self.zone_id}/dns_records", headers=headers, json=payload
                )
            response.raise_for_status()
            result = response.json()
            if not result.get("success"):
                raise APIError("CLOUDFLARE_ERROR", "Cloudflare rejeitou a configuração DNS.", 502, result)
            item = result["result"]
            return DNSRecordResult(
                record_id=item["id"], name=item["name"], content=item["content"], proxied=item["proxied"]
            )

    async def delete_record(self, record_id: str) -> None:
        if not self.configured or not record_id:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}", headers=headers
            )
            if response.status_code not in {200, 404}:
                response.raise_for_status()
