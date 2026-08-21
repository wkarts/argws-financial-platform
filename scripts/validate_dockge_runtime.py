#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deployments/dockge/compose.yaml"
ENV_EXAMPLE = ROOT / "deployments/dockge/.env.example"


def fail(message: str) -> None:
    raise SystemExit(f"[ERRO] {message}")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def volume_source(item: object) -> str | None:
    if isinstance(item, str):
        # Compose short syntax is SOURCE:TARGET[:MODE]. Use rsplit because
        # ${FINANCIAL_DATA_ROOT:-.} itself contains a colon.
        parts = item.rsplit(":", 2)
        if len(parts) >= 2:
            return parts[0]
        return item
    if isinstance(item, dict):
        source = item.get("source")
        return str(source) if source is not None else None
    return None


def main() -> int:
    compose_text = COMPOSE.read_text(encoding="utf-8")
    data = yaml.safe_load(compose_text)
    if not isinstance(data, dict):
        fail("Compose Dockge inválido")

    services = data.get("services")
    if not isinstance(services, dict):
        fail("Compose Dockge sem services")

    if data.get("volumes"):
        fail("Dockge não deve usar volumes Docker nomeados; use ./data-*")

    for service_name, service in services.items():
        if isinstance(service, dict) and "build" in service:
            fail(f"{service_name} ainda depende de build local")

    forbidden = ("backend/Dockerfile", "frontend/Dockerfile", "infrastructure/nginx/gateway.conf")
    for token in forbidden:
        if token in compose_text:
            fail(f"Dockge ainda referencia arquivo local: {token}")

    required_services = {
        "financial-storage-init",
        "financial-postgres",
        "financial-redis",
        "financial-rabbitmq",
        "financial-minio",
        "financial-minio-init",
        "financial-migrate",
        "financial-migrate-tenants",
        "financial-bootstrap",
        "financial-api",
        "financial-worker-default",
        "financial-worker-billing",
        "financial-worker-notifications",
        "financial-worker-backups",
        "financial-beat",
        "financial-web",
        "financial-gateway",
    }
    missing_services = sorted(required_services - set(services))
    if missing_services:
        fail(f"Serviços ausentes no Dockge: {missing_services}")

    required_bind_sources = {
        "${FINANCIAL_DATA_ROOT:-.}/data-postgres",
        "${FINANCIAL_DATA_ROOT:-.}/data-redis",
        "${FINANCIAL_DATA_ROOT:-.}/data-rabbitmq",
        "${FINANCIAL_DATA_ROOT:-.}/data-minio",
        "${FINANCIAL_DATA_ROOT:-.}/data-backups",
        "${FINANCIAL_DATA_ROOT:-.}/data-runtime",
        "${FINANCIAL_DATA_ROOT:-.}/data-celery",
    }
    found_sources: set[str] = set()
    for service in services.values():
        if not isinstance(service, dict):
            continue
        for item in service.get("volumes", []) or []:
            source = volume_source(item)
            if source:
                found_sources.add(source)

    missing_binds = sorted(required_bind_sources - found_sources)
    if missing_binds:
        fail(f"Bind mounts data-* ausentes: {missing_binds}")

    env = parse_env(ENV_EXAMPLE)
    if env.get("APP_PULL_POLICY") != "always":
        fail("APP_PULL_POLICY do Dockge deve ser always")
    if env.get("FINANCIAL_DATA_ROOT") != ".":
        fail("FINANCIAL_DATA_ROOT do Dockge deve ser . para persistir em ./data-*")

    expected_images = {
        "BACKEND_IMAGE": "ghcr.io/wkarts/argws-financial-api:latest",
        "FRONTEND_IMAGE": "ghcr.io/wkarts/argws-financial-web:latest",
        "GATEWAY_IMAGE": "ghcr.io/wkarts/argws-financial-gateway:latest",
    }
    for key, expected in expected_images.items():
        if env.get(key) != expected:
            fail(f"{key} deve ser {expected}")

    print("Dockge runtime: PASS")
    print("- image-only: OK")
    print("- GHCR latest: OK")
    print("- bind mounts ./data-*: OK")
    print("- named volumes: ausentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
