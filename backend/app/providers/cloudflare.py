from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import APIError


@dataclass(frozen=True, slots=True)
class DNSRecordResult:
    record_id: str
    name: str
    content: str
    proxied: bool
    record_type: str = "CNAME"


class CloudflareDNSProvider:
    base_url = "https://api.cloudflare.com/client/v4"

    def __init__(self) -> None:
        self.enabled = settings.cloudflare_enabled
        self.zone_id = settings.cloudflare_zone_id
        self.token = settings.cloudflare_api_token

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.zone_id and self.token)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _require_configured(self) -> None:
        if not self.configured:
            raise APIError("CLOUDFLARE_NOT_CONFIGURED", "Cloudflare não está configurado.", 503)

    async def list_records(self, hostname: str, record_type: str | None = None) -> list[dict[str, Any]]:
        self._require_configured()
        params: dict[str, str] = {"name": hostname.lower().strip().rstrip(".")}
        if record_type:
            params["type"] = record_type.upper()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/zones/{self.zone_id}/dns_records",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            result = response.json()
        if not result.get("success"):
            raise APIError("CLOUDFLARE_ERROR", "Cloudflare rejeitou a consulta DNS.", 502, result)
        records = result.get("result", [])
        return [item for item in records if isinstance(item, dict)]

    async def upsert_record(
        self,
        hostname: str,
        content: str,
        *,
        record_type: str = "CNAME",
        proxied: bool | None = None,
    ) -> DNSRecordResult:
        self._require_configured()
        clean_name = hostname.lower().strip().rstrip(".")
        clean_content = content.strip().rstrip(".")
        desired_type = record_type.upper()
        proxied_value = settings.cloudflare_proxied if proxied is None else proxied
        existing = await self.list_records(clean_name)
        same_type = next((item for item in existing if str(item.get("type", "")).upper() == desired_type), None)

        payload = {
            "type": desired_type,
            "name": clean_name,
            "content": clean_content,
            "proxied": proxied_value,
            "ttl": 1,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            if same_type:
                record_id = str(same_type["id"])
                response = await client.put(
                    f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}",
                    headers=self.headers,
                    json=payload,
                )
            else:
                # A/CNAME/AAAA no hostname gerenciado podem bloquear a criação do
                # tipo desejado. Como o hostname é reservado à plataforma, convergimos
                # somente esses tipos de endereço e preservamos TXT/MX/outros registros.
                blockers = [
                    item
                    for item in existing
                    if str(item.get("type", "")).upper() in {"A", "AAAA", "CNAME"}
                ]
                for blocker in blockers:
                    delete_response = await client.delete(
                        f"{self.base_url}/zones/{self.zone_id}/dns_records/{blocker['id']}",
                        headers=self.headers,
                    )
                    if delete_response.status_code not in {200, 404}:
                        delete_response.raise_for_status()
                response = await client.post(
                    f"{self.base_url}/zones/{self.zone_id}/dns_records",
                    headers=self.headers,
                    json=payload,
                )
            response.raise_for_status()
            result = response.json()

        if not result.get("success"):
            raise APIError("CLOUDFLARE_ERROR", "Cloudflare rejeitou a configuração DNS.", 502, result)
        item = result["result"]
        return DNSRecordResult(
            record_id=str(item["id"]),
            name=str(item["name"]),
            content=str(item["content"]),
            proxied=bool(item.get("proxied", False)),
            record_type=str(item.get("type", desired_type)),
        )

    async def upsert_cname(self, hostname: str, target: str, proxied: bool | None = None) -> DNSRecordResult:
        return await self.upsert_record(hostname, target, record_type="CNAME", proxied=proxied)

    async def ensure_managed_wildcard(self) -> DNSRecordResult:
        """Garante origem DNS-only e wildcard usados pelos domínios internos.

        Em ``wildcard`` o registro é infraestrutura compartilhada da plataforma.
        A criação/renovação de certificado fica com ACME e a publicação no host com
        CloudPanel. Se um token restrito conseguir operar o DNS-01 do ACME, mas a
        API REST negar leitura/reconciliação com 401/403, o tenant não deve ser
        marcado como falho por causa dessa dependência externa já compartilhada.

        Fora desse caso, erros continuam sendo propagados normalmente.
        """

        wildcard = f"*.{settings.tenant_domain_root}".lower().strip(".")
        platform = settings.platform_domain.lower().strip().rstrip(".")
        target = (settings.cloudflare_tenant_record_target or platform).lower().strip().rstrip(".")

        try:
            if target != platform:
                platform_records = await self.list_records(platform)
                source = next(
                    (
                        item
                        for record_type in ("A", "AAAA", "CNAME")
                        for item in platform_records
                        if str(item.get("type", "")).upper() == record_type
                    ),
                    None,
                )
                if source is None:
                    raise APIError(
                        "CLOUDFLARE_ORIGIN_NOT_FOUND",
                        "Não foi possível derivar a origem DNS do domínio principal para criar o wildcard.",
                        409,
                        {"hostname": platform},
                    )
                await self.upsert_record(
                    target,
                    str(source.get("content", "")),
                    record_type=str(source.get("type", "A")),
                    proxied=False,
                )

            return await self.upsert_cname(wildcard, target, proxied=False)
        except httpx.HTTPStatusError as exc:
            if (
                settings.cloudflare_provisioning_mode == "wildcard"
                and exc.response.status_code in {401, 403}
            ):
                return DNSRecordResult(
                    record_id="",
                    name=wildcard,
                    content=target,
                    proxied=False,
                    record_type="EXTERNAL_WILDCARD",
                )
            raise

    async def delete_record(self, record_id: str) -> None:
        if not self.configured or not record_id:
            return
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}", headers=self.headers
            )
            if response.status_code not in {200, 404}:
                response.raise_for_status()
