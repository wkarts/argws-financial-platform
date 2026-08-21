from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass(frozen=True, slots=True)
class EvolutionConfig:
    base_url: str
    api_key: str
    instance: str
    send_text_path: str = "/message/sendText/{instance}"
    send_media_path: str = "/message/sendMedia/{instance}"
    timeout: int = 30


@dataclass(frozen=True, slots=True)
class EvolutionMessageResult:
    external_id: str | None
    status: str
    raw: dict[str, Any]


class EvolutionWhatsAppProvider:
    def __init__(self, config: EvolutionConfig) -> None:
        self.config = config

    def _url(self, path: str) -> str:
        resolved = path.format(instance=self.config.instance)
        return f"{self.config.base_url.rstrip('/')}/{resolved.lstrip('/')}"

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def send_text(self, number: str, text: str) -> EvolutionMessageResult:
        payload = {"number": number, "text": text, "delay": 0, "linkPreview": True}
        headers = {"apikey": self.config.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(self._url(self.config.send_text_path), headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        external_id = (
            data.get("key", {}).get("id")
            or data.get("message", {}).get("key", {}).get("id")
            or data.get("id")
        )
        return EvolutionMessageResult(external_id=external_id, status="SENT", raw=data)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def send_media(
        self, number: str, media_url: str, *, caption: str = "", filename: str = "documento.pdf"
    ) -> EvolutionMessageResult:
        payload = {
            "number": number,
            "mediatype": "document",
            "mimetype": "application/pdf",
            "caption": caption,
            "media": media_url,
            "fileName": filename,
        }
        headers = {"apikey": self.config.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(self._url(self.config.send_media_path), headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        external_id = data.get("key", {}).get("id") or data.get("id")
        return EvolutionMessageResult(external_id=external_id, status="SENT", raw=data)

    async def health(self) -> dict[str, Any]:
        path = f"/instance/connectionState/{self.config.instance}"
        headers = {"apikey": self.config.api_key}
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(self._url(path), headers=headers)
            response.raise_for_status()
            return response.json()
