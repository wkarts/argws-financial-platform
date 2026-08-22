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

    required_services = {
        "financial-preflight",
        "financial-domain-init",
        "financial-storage-init",
        "financial-acme",
        "financial-cloudpanel-agent",
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

    publishers = [
        name for name, service in services.items()
        if isinstance(service, dict) and service.get("ports")
    ]
    if publishers != ["financial-gateway"]:
        fail(f"Somente financial-gateway pode publicar porta; encontrado: {publishers}")

    expected_runtime = {
        "financial-preflight": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-domain-init": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-api": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
        "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
        "financial-acme": "ghcr.io/wkarts/argws-financial-acme:latest",
        "financial-cloudpanel-agent": "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest",
    }
    for service_name, expected_image in expected_runtime.items():
        service = services.get(service_name)
        if not isinstance(service, dict):
            fail(f"{service_name} inválido no Compose Dockge")
        if service.get("pull_policy") != "always":
            fail(f"{service_name} deve usar pull_policy: always")
        if service.get("image") != expected_image:
            fail(f"{service_name} deve usar imagem fixa {expected_image}")
        if service_name != "financial-gateway" and service.get("ports"):
            fail(f"{service_name} não pode publicar porta")

    agent = services["financial-cloudpanel-agent"]
    if agent.get("privileged") is not True:
        fail("financial-cloudpanel-agent deve ser o único helper privilegiado")
    if agent.get("pid") != "host" or agent.get("network_mode") != "host":
        fail("financial-cloudpanel-agent precisa usar pid/network host")
    if "/:/host:rw" not in (agent.get("volumes") or []):
        fail("financial-cloudpanel-agent precisa montar o host em /host:rw")

    required_bind_sources = {
        "${FINANCIAL_DATA_ROOT:-.}/data-postgres",
        "${FINANCIAL_DATA_ROOT:-.}/data-redis",
        "${FINANCIAL_DATA_ROOT:-.}/data-rabbitmq",
        "${FINANCIAL_DATA_ROOT:-.}/data-minio",
        "${FINANCIAL_DATA_ROOT:-.}/data-backups",
        "${FINANCIAL_DATA_ROOT:-.}/data-runtime",
        "${FINANCIAL_DATA_ROOT:-.}/data-celery",
        "${FINANCIAL_DATA_ROOT:-.}/data-acme",
        "${FINANCIAL_DATA_ROOT:-.}/data-certs",
        "${FINANCIAL_DATA_ROOT:-.}/data-cloudpanel-agent",
    }
    missing_binds = sorted(source for source in required_bind_sources if source not in compose_text)
    if missing_binds:
        fail(f"Bind mounts data-* ausentes: {missing_binds}")

    env = parse_env(ENV_EXAMPLE)
    required_env = {
        "PLATFORM_DOMAIN",
        "CONTROL_PLANE_HOST",
        "API_HOST",
        "TENANT_DOMAIN_ROOT",
        "GATEWAY_PORT",
        "FINANCIAL_DATA_ROOT",
        "APP_SECRET_KEY",
        "FIELD_ENCRYPTION_KEY",
        "INTERNAL_SERVICES_PASSWORD",
        "INITIAL_ADMIN_PASSWORD",
        "DOMAIN_RECONCILIATION_TOKEN",
        "BANKING_WEBHOOK_SECRET",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID",
        "CLOUDFLARE_PROVISIONING_MODE",
        "ACME_DOMAIN",
        "ACME_EMAIL",
        "CLOUDPANEL_SITE_DOMAIN",
        "CLOUDPANEL_WILDCARD_DOMAIN",
    }
    missing_env = sorted(required_env - set(env))
    if missing_env:
        fail(f"Variáveis obrigatórias ausentes no exemplo Dockge: {missing_env}")
    if env.get("FINANCIAL_DATA_ROOT") != ".":
        fail("FINANCIAL_DATA_ROOT do Dockge deve ser .")
    if env.get("CLOUDFLARE_PROVISIONING_MODE") != "wildcard":
        fail("Dockge/CloudPanel deve usar provisionamento wildcard")
    if env.get("CLOUDFLARE_ENABLED", "").lower() != "true":
        fail("Cloudflare deve vir habilitada no exemplo CloudPanel automático")

    forbidden_env = {
        "RABBITMQ_MANAGEMENT_BIND_IP",
        "RABBITMQ_MANAGEMENT_PORT",
        "MINIO_CONSOLE_BIND_IP",
        "MINIO_CONSOLE_PORT",
        "PROMETHEUS_BIND_IP",
        "PROMETHEUS_PORT",
        "GRAFANA_BIND_IP",
        "GRAFANA_PORT",
        "BACKEND_IMAGE",
        "FRONTEND_IMAGE",
        "GATEWAY_IMAGE",
        "APP_PULL_POLICY",
    }
    present_forbidden = sorted(forbidden_env & set(env))
    if present_forbidden:
        fail(f"Exemplo Dockge ainda expõe configuração redundante/interna: {present_forbidden}")

    print("Dockge runtime: PASS")
    print("- image-only / GHCR latest: OK")
    print("- única porta publicada: financial-gateway")
    print("- wildcard DNS + ACME + CloudPanel agent: OK")
    print("- credenciais centrais sem repetição: OK")
    print("- bind mounts ./data-*: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
