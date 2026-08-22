#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
STACKS = [
    ROOT / "compose.yaml",
    ROOT / "deployments/docker/compose.images.yaml",
    ROOT / "deployments/production/compose.yaml",
    ROOT / "deployments/dockge/compose.yaml",
    ROOT / "deployments/cloudpanel/compose.yaml",
    ROOT / "deployments/portainer/stack.yaml",
]
ENV_FILES = [
    ROOT / ".env.example",
    ROOT / "deployments/docker/.env.example",
    ROOT / "deployments/production/.env.example",
    ROOT / "deployments/dockge/.env.example",
    ROOT / "deployments/cloudpanel/.env.example",
    ROOT / "deployments/portainer/.env.example",
    ROOT / "deployments/portainer/stack.env.example",
]
REQUIRED_SERVICES = {
    "financial-preflight", "financial-domain-init", "financial-storage-init", "financial-monitoring-init",
    "financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio", "financial-minio-init",
    "financial-migrate", "financial-migrate-tenants", "financial-bootstrap", "financial-api",
    "financial-worker-default", "financial-worker-billing", "financial-worker-notifications",
    "financial-worker-backups", "financial-beat", "financial-web", "financial-prometheus", "financial-grafana",
    "financial-acme", "financial-cloudpanel-agent", "financial-gateway",
}
EXPECTED_IMAGES = {
    "financial-api": "ghcr.io/wkarts/argws-financial-api:latest",
    "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
    "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
    "financial-acme": "ghcr.io/wkarts/argws-financial-acme:latest",
    "financial-cloudpanel-agent": "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest",
}
errors: list[str] = []

if (ROOT / "deployments/portainer/stack-build.yaml").exists():
    errors.append("deployments/portainer/stack-build.yaml não deve existir; build local fica somente em compose.local-build.yaml")

for path in STACKS:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: arquivo ausente")
        continue
    text = path.read_text(encoding="utf-8")
    if "\nbuild:" in text or "\n    build:" in text or "dockerfile:" in text:
        errors.append(f"{path.relative_to(ROOT)}: deployment de produção contém build local")
    try:
        data = yaml.safe_load(text) or {}
    except Exception as exc:
        errors.append(f"{path.relative_to(ROOT)}: YAML inválido: {exc}")
        continue
    services = data.get("services") or {}
    missing = sorted(REQUIRED_SERVICES - set(services))
    if missing:
        errors.append(f"{path.relative_to(ROOT)}: serviços ausentes: {', '.join(missing)}")
    publishers = [name for name, service in services.items() if service.get("ports")]
    if publishers != ["financial-gateway"]:
        errors.append(f"{path.relative_to(ROOT)}: somente financial-gateway pode publicar porta; encontrados: {publishers}")
    for service, expected in EXPECTED_IMAGES.items():
        value = (services.get(service) or {}).get("image")
        if value != expected:
            errors.append(f"{path.relative_to(ROOT)}: {service}.image deve ser {expected!r}, encontrado {value!r}")
    for internal in ("financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio", "financial-prometheus", "financial-grafana"):
        if (services.get(internal) or {}).get("ports"):
            errors.append(f"{path.relative_to(ROOT)}: {internal} não pode publicar porta no host")

for path in ENV_FILES:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: env example ausente")
        continue
    text = path.read_text(encoding="utf-8")
    required = [
        "APP_NAME=ARGWS Financial Platform",
        "PLATFORM_DOMAIN=finance.argws.com.br",
        "CONTROL_PLANE_HOST=control.finance.argws.com.br",
        "ADMIN_HOST=admin.finance.argws.com.br",
        "API_HOST=api.finance.argws.com.br",
        "DEMO_HOST=demo.finance.argws.com.br",
        "TENANT_DOMAIN_ROOT=finance.argws.com.br",
        "VITE_APP_NAME=ARGWS Financial Platform",
    ]
    for item in required:
        if item not in text:
            errors.append(f"{path.relative_to(ROOT)}: esperado {item}")
    if "APP_NAME=ARGWS Financeiro" in text or "VITE_APP_NAME=ARGWS Financeiro" in text:
        errors.append(f"{path.relative_to(ROOT)}: nome da plataforma foi alterado indevidamente")

for path in (
    ROOT / "infrastructure/nginx/gateway.conf.template",
    ROOT / "infrastructure/docker/gateway/landing/index.html",
    ROOT / "infrastructure/docker/gateway/Dockerfile",
):
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: arquivo obrigatório ausente")

if errors:
    print("DEPLOYMENT_PARITY=FAIL")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("DEPLOYMENT_PARITY=PASS")
print(f"STACKS={len(STACKS)}")
print(f"REQUIRED_SERVICES={len(REQUIRED_SERVICES)}")
print("PUBLIC_HOST_PORT=financial-gateway")
print("DEFAULT_DOMAIN=finance.argws.com.br")
