#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = [
    ROOT / "compose.yaml",
    ROOT / "deployments/docker/compose.images.yaml",
    ROOT / "deployments/dockge/compose.yaml",
    ROOT / "deployments/cloudpanel/compose.yaml",
    ROOT / "deployments/production/compose.yaml",
    ROOT / "deployments/portainer/stack.yaml",
]


def fail(message: str) -> None:
    raise SystemExit(f"[ERRO] {message}")


def has_build(value: object) -> bool:
    if isinstance(value, dict):
        if "build" in value:
            return True
        return any(has_build(item) for item in value.values())
    if isinstance(value, list):
        return any(has_build(item) for item in value)
    return False


def main() -> int:
    reference: bytes | None = None
    for path in RUNTIMES:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            fail(f"YAML inválido: {path.relative_to(ROOT)}")
        if has_build(data):
            fail(f"build local encontrado em deployment: {path.relative_to(ROOT)}")
        services = data.get("services")
        if not isinstance(services, dict):
            fail(f"services ausente em {path.relative_to(ROOT)}")

        publishers = [name for name, service in services.items() if isinstance(service, dict) and service.get("ports")]
        if publishers != ["financial-gateway"]:
            fail(f"{path.relative_to(ROOT)} publica portas em {publishers}; esperado somente financial-gateway")

        for internal in ("financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio"):
            service = services.get(internal)
            if not isinstance(service, dict):
                fail(f"{internal} ausente em {path.relative_to(ROOT)}")
            if service.get("ports"):
                fail(f"{internal} não pode publicar porta no host em {path.relative_to(ROOT)}")

        gateway = services.get("financial-gateway")
        if not isinstance(gateway, dict) or len(gateway.get("ports") or []) != 1:
            fail(f"gateway precisa de exatamente um bind em {path.relative_to(ROOT)}")

        for name, expected in {
            "financial-preflight": "ghcr.io/wkarts/argws-financial-api:latest",
            "financial-api": "ghcr.io/wkarts/argws-financial-api:latest",
            "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
            "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
        }.items():
            service = services.get(name)
            if not isinstance(service, dict) or service.get("image") != expected:
                fail(f"{name} deve usar {expected} em {path.relative_to(ROOT)}")
            if service.get("pull_policy") != "always":
                fail(f"{name} deve usar pull_policy=always em {path.relative_to(ROOT)}")

        content = path.read_bytes()
        if reference is None:
            reference = content
        elif content != reference:
            fail(f"runtime divergente do compose canônico: {path.relative_to(ROOT)}")

    local = yaml.safe_load((ROOT / "compose.local-build.yaml").read_text(encoding="utf-8"))
    if not has_build(local):
        fail("compose.local-build.yaml não contém build local explícito")

    for path in (ROOT / "deployments").rglob("*.yaml"):
        if path.name == "stack-build.yaml":
            disabled = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if has_build(disabled):
                fail("stack-build.yaml do Portainer não pode conter build")
            continue
        if path in RUNTIMES or path.name.endswith(".override.yaml"):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if has_build(data):
            fail(f"deployment auxiliar contém build local: {path.relative_to(ROOT)}")

    print("Runtime contract: PASS")
    print("- deployments image-only: OK")
    print("- única porta publicada: financial-gateway")
    print("- serviços internos sem host ports: OK")
    print("- GHCR :latest: OK")
    print("- build local isolado em compose.local-build.yaml: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
