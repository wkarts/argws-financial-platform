#!/usr/bin/env python3
from __future__ import annotations

import subprocess
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
    text = COMPOSE.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    services = data.get("services") if isinstance(data, dict) else None
    if not isinstance(services, dict):
        fail("Compose Dockge inválido ou sem services")
    if data.get("volumes"):
        fail("Dockge não deve usar volumes Docker nomeados; use ./data-*")
    for name, service in services.items():
        if isinstance(service, dict) and "build" in service:
            fail(f"{name} ainda depende de build local")
    required = {
        "financial-preflight", "financial-domain-init", "financial-storage-init", "financial-monitoring-init",
        "financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio", "financial-minio-init",
        "financial-migrate", "financial-migrate-tenants", "financial-bootstrap", "financial-api",
        "financial-worker-default", "financial-worker-billing", "financial-worker-notifications",
        "financial-worker-backups", "financial-beat", "financial-web", "financial-prometheus", "financial-grafana",
        "financial-acme", "financial-cloudpanel-agent", "financial-gateway",
    }
    missing = sorted(required - set(services))
    if missing:
        fail(f"Serviços ausentes no Dockge: {missing}")
    publishers = [name for name, service in services.items() if isinstance(service, dict) and service.get("ports")]
    if publishers != ["financial-gateway"]:
        fail(f"Somente financial-gateway pode publicar porta; encontrado: {publishers}")
    expected = {
        "financial-preflight": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-domain-init": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-api": "ghcr.io/wkarts/argws-financial-api:latest",
        "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
        "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
        "financial-acme": "ghcr.io/wkarts/argws-financial-acme:latest",
        "financial-cloudpanel-agent": "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest",
    }
    for name, image in expected.items():
        service = services.get(name) or {}
        if service.get("image") != image:
            fail(f"{name} deve usar {image}")
        if service.get("pull_policy") != "always":
            fail(f"{name} deve usar pull_policy: always")
    for internal in ("financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio", "financial-prometheus", "financial-grafana"):
        if (services.get(internal) or {}).get("ports"):
            fail(f"{internal} não pode publicar porta no host")
    for folder in (
        "data-postgres", "data-redis", "data-rabbitmq", "data-minio", "data-backups", "data-runtime",
        "data-celery", "data-prometheus", "data-grafana", "data-monitoring", "data-acme", "data-certs", "data-cloudpanel-agent",
    ):
        if folder not in text:
            fail(f"Bind mount ausente: {folder}")
    env = parse_env(ENV_EXAMPLE)
    expected_env = {
        "APP_NAME": "ARGWS Financial Platform",
        "PLATFORM_DOMAIN": "finance.argws.com.br",
        "CONTROL_PLANE_HOST": "control.finance.argws.com.br",
        "ADMIN_HOST": "admin.finance.argws.com.br",
        "API_HOST": "api.finance.argws.com.br",
        "DEMO_HOST": "demo.finance.argws.com.br",
        "TENANT_DOMAIN_ROOT": "finance.argws.com.br",
        "FINANCIAL_DATA_ROOT": ".",
        "BOOTSTRAP_DEMO_TENANT": "true",
        "VITE_APP_NAME": "ARGWS Financial Platform",
    }
    for key, value in expected_env.items():
        if env.get(key) != value:
            fail(f"{key} deve ser {value!r}, encontrado {env.get(key)!r}")
    if env.get("CLOUDFLARE_PROVISIONING_MODE") != "wildcard":
        fail("CLOUDFLARE_PROVISIONING_MODE deve ser wildcard")
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_deployment_parity.py")], check=True)
    print("Dockge runtime: PASS")
    print("- branding: ARGWS Financial Platform")
    print("- domínio padrão: finance.argws.com.br")
    print("- landing/demo/control/admin/api/wildcard: OK")
    print("- image-only / GHCR latest: OK")
    print("- única porta publicada: financial-gateway")
    print("- Prometheus/Grafana internos: OK")
    print("- bind mounts ./data-*: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
