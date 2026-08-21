#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

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

    expected_runtime = {
        "financial-api": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
        "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
    }
    for service_name, expected_image in expected_runtime.items():
        service = services.get(service_name)
        if not isinstance(service, dict):
            fail(f"{service_name} inválido no Compose Dockge")
        if service.get("pull_policy") != "always":
            fail(f"{service_name} deve usar pull_policy: always fixo no Compose Dockge")
        if service.get("image") != expected_image:
            fail(f"{service_name} deve usar imagem fixa {expected_image}")

    required_bind_sources = {
        "${FINANCIAL_DATA_ROOT:-.}/data-postgres",
        "${FINANCIAL_DATA_ROOT:-.}/data-redis",
        "${FINANCIAL_DATA_ROOT:-.}/data-rabbitmq",
        "${FINANCIAL_DATA_ROOT:-.}/data-minio",
        "${FINANCIAL_DATA_ROOT:-.}/data-backups",
        "${FINANCIAL_DATA_ROOT:-.}/data-runtime",
        "${FINANCIAL_DATA_ROOT:-.}/data-celery",
    }
    missing_binds = sorted(source for source in required_bind_sources if source not in compose_text)
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
    print("- pull_policy always fixo: OK")
    print("- imagens GHCR latest fixas: OK")
    print("- bind mounts ./data-*: OK")
    print("- named volumes: ausentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
