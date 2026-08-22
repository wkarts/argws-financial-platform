from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.providers.cloudflare import CloudflareDNSProvider


async def reconcile_managed_wildcard() -> dict[str, str | bool]:
    if not settings.cloudflare_enabled:
        return {"status": "SKIPPED", "reason": "cloudflare_disabled"}
    if settings.cloudflare_provisioning_mode != "wildcard":
        return {"status": "SKIPPED", "reason": "records_mode"}

    provider = CloudflareDNSProvider()
    if not provider.configured:
        raise RuntimeError("Cloudflare habilitado, mas token/zone_id não estão configurados.")

    result = await provider.ensure_managed_wildcard()
    return {
        "status": "READY",
        "hostname": result.name,
        "target": result.content,
        "proxied": result.proxied,
    }


async def main() -> int:
    report = await reconcile_managed_wildcard()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
