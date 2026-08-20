from __future__ import annotations

from app.core.errors import APIError
from app.providers.banking.base import BankingProvider
from app.providers.banking.sandbox import SandboxBankingProvider


class BankingProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BankingProvider] = {"SANDBOX": SandboxBankingProvider()}

    def register(self, name: str, provider: BankingProvider) -> None:
        self._providers[name.upper()] = provider

    def get(self, name: str) -> BankingProvider:
        provider = self._providers.get(name.upper())
        if provider is None:
            raise APIError(
                "BANKING_PROVIDER_NOT_AVAILABLE",
                "Provider bancário não instalado ou não homologado.",
                422,
                {"provider": name},
            )
        return provider


banking_providers = BankingProviderRegistry()
