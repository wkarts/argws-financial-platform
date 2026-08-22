#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
WARNINGS: list[str] = []
METRICS: dict[str, Any] = {}

RUNTIME_FILES = [
    ROOT / "compose.yaml",
    ROOT / "deployments/docker/compose.images.yaml",
    ROOT / "deployments/dockge/compose.yaml",
    ROOT / "deployments/cloudpanel/compose.yaml",
    ROOT / "deployments/production/compose.yaml",
    ROOT / "deployments/portainer/stack.yaml",
]
OVERRIDE_FILES = [
    ROOT / "deployments/development/compose.override.yaml",
    ROOT / "deployments/staging/compose.override.yaml",
]
CORE_SERVICES = {
    "financial-preflight", "financial-storage-init", "financial-postgres", "financial-redis",
    "financial-rabbitmq", "financial-minio", "financial-minio-init", "financial-migrate",
    "financial-migrate-tenants", "financial-bootstrap", "financial-api", "financial-worker-default",
    "financial-worker-billing", "financial-worker-notifications", "financial-worker-backups",
    "financial-beat", "financial-web", "financial-gateway",
}
API_IMAGE_SERVICES = {
    "financial-preflight", "financial-migrate", "financial-migrate-tenants", "financial-bootstrap",
    "financial-api", "financial-worker-default", "financial-worker-billing",
    "financial-worker-notifications", "financial-worker-backups", "financial-beat",
}
REQUIRED_DATA_TOKENS = {
    "data-postgres", "data-redis", "data-rabbitmq", "data-minio",
    "data-backups", "data-runtime", "data-celery",
}


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        error(f"Arquivo YAML ausente: {path.relative_to(ROOT)}")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"YAML inválido em {path.relative_to(ROOT)}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        error(f"Arquivo de ambiente ausente: {path.relative_to(ROOT)}")
        return values
    seen: set[str] = set()
    duplicates: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in seen:
            duplicates.add(key)
        seen.add(key)
        values[key] = value.strip()
    if duplicates:
        error(f"Variáveis duplicadas em {path.relative_to(ROOT)}: {sorted(duplicates)}")
    return values


def required_files() -> None:
    paths = [
        "README.md", "VERSION", "CHANGELOG.md", "RELEASE_NOTES.md", ".env.example",
        "compose.yaml", "compose.local-build.yaml", "Makefile",
        "backend/Dockerfile", "backend/app/version.py", "backend/app/preflight.py",
        "frontend/Dockerfile", "frontend/vite.config.ts", "frontend/package.json",
        "scripts/generate_secrets.py", "scripts/package_release.py", "scripts/package_dockge_stack.py",
        "scripts/validate_dockge_runtime.py", "scripts/validate_runtime_contract.py",
        "deployments/dockge/compose.yaml", "deployments/dockge/.env.example",
        "deployments/docker/compose.images.yaml", "deployments/cloudpanel/compose.yaml",
        "deployments/production/compose.yaml", "deployments/portainer/stack.yaml",
        ".github/workflows/ci.yml", ".github/workflows/publish.yml",
    ]
    for relative in paths:
        if not (ROOT / relative).is_file():
            error(f"Arquivo obrigatório ausente: {relative}")


def validate_python() -> None:
    count = 0
    for base in (ROOT / "backend", ROOT / "scripts"):
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                error(f"Python inválido: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    METRICS["python_files"] = count


def validate_shell() -> None:
    bash = shutil.which("bash")
    if bash is None:
        warning("bash indisponível; scripts shell não foram validados")
        return
    count = 0
    for path in sorted(ROOT.rglob("*.sh")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        count += 1
        result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, check=False)
        if result.returncode:
            error(f"Shell inválido: {path.relative_to(ROOT)}: {result.stderr.strip()}")
    METRICS["shell_scripts"] = count


def _service_ports(service: Any) -> list[Any]:
    if not isinstance(service, dict):
        return []
    ports = service.get("ports") or []
    return list(ports) if isinstance(ports, list) else [ports]


def _has_build(value: Any) -> bool:
    if isinstance(value, dict):
        if "build" in value:
            return True
        return any(_has_build(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_build(item) for item in value)
    return False


def validate_runtime_compose(path: Path) -> None:
    data = load_yaml(path)
    services = data.get("services", {})
    if not isinstance(services, dict):
        error(f"Compose sem services: {path.relative_to(ROOT)}")
        return
    missing = sorted(CORE_SERVICES - set(services))
    if missing:
        error(f"Serviços obrigatórios ausentes em {path.relative_to(ROOT)}: {missing}")
    if _has_build(data):
        error(f"Deploy não pode conter build local: {path.relative_to(ROOT)}")

    published = [name for name, service in services.items() if _service_ports(service)]
    if published != ["financial-gateway"]:
        error(f"Somente financial-gateway pode publicar porta em {path.relative_to(ROOT)}; encontrado: {published}")
    ports = _service_ports(services.get("financial-gateway", {}))
    if len(ports) != 1 or ":80" not in str(ports[0]):
        error(f"Gateway deve publicar exatamente uma porta HTTP em {path.relative_to(ROOT)}")

    expected_api = "ghcr.io/wkarts/argws-financial-api:latest"
    for name in API_IMAGE_SERVICES:
        service = services.get(name)
        if isinstance(service, dict) and service.get("image") != expected_api:
            error(f"{path.relative_to(ROOT)}:{name} deve usar {expected_api}")
        if isinstance(service, dict) and service.get("pull_policy") != "always":
            error(f"{path.relative_to(ROOT)}:{name} deve usar pull_policy=always")

    for name, image in {
        "financial-web": "ghcr.io/wkarts/argws-financial-web:latest",
        "financial-gateway": "ghcr.io/wkarts/argws-financial-gateway:latest",
    }.items():
        service = services.get(name)
        if isinstance(service, dict) and service.get("image") != image:
            error(f"{path.relative_to(ROOT)}:{name} deve usar {image}")
        if isinstance(service, dict) and service.get("pull_policy") != "always":
            error(f"{path.relative_to(ROOT)}:{name} deve usar pull_policy=always")

    preflight = services.get("financial-preflight", {})
    if not isinstance(preflight, dict) or preflight.get("network_mode") != "none":
        error(f"financial-preflight deve executar sem rede em {path.relative_to(ROOT)}")

    text = path.read_text(encoding="utf-8")
    missing_data = sorted(token for token in REQUIRED_DATA_TOKENS if token not in text)
    if missing_data:
        error(f"Persistência data-* incompleta em {path.relative_to(ROOT)}: {missing_data}")
    if data.get("volumes"):
        error(f"Runtime deve usar bind mounts data-* e não named volumes: {path.relative_to(ROOT)}")


def validate_deployment_overrides() -> None:
    for path in OVERRIDE_FILES:
        data = load_yaml(path)
        if _has_build(data):
            error(f"Override de deployment não pode conter build: {path.relative_to(ROOT)}")
        services = data.get("services", {}) if isinstance(data, dict) else {}
        if isinstance(services, dict):
            published = [name for name, service in services.items() if _service_ports(service)]
            if any(name != "financial-gateway" for name in published):
                error(f"Override publica porta interna em {path.relative_to(ROOT)}: {published}")

    disabled = load_yaml(ROOT / "deployments/portainer/stack-build.yaml")
    if _has_build(disabled):
        error("deployments/portainer/stack-build.yaml precisa permanecer desabilitado, sem build")
    if disabled.get("services") not in ({}, None):
        error("stack-build.yaml desabilitado não deve declarar serviços")

    local = load_yaml(ROOT / "compose.local-build.yaml")
    if not _has_build(local):
        error("compose.local-build.yaml deve ser o único modelo explícito de build local")
    local_services = local.get("services", {}) if isinstance(local, dict) else {}
    for required in ("financial-api", "financial-web", "financial-gateway", "financial-preflight"):
        service = local_services.get(required, {}) if isinstance(local_services, dict) else {}
        if not isinstance(service, dict) or "build" not in service:
            error(f"compose.local-build.yaml sem build explícito de {required}")


def validate_compose() -> None:
    for path in RUNTIME_FILES:
        validate_runtime_compose(path)
    validate_deployment_overrides()
    canonical = (ROOT / "compose.yaml").read_bytes()
    for path in RUNTIME_FILES[1:]:
        if path.read_bytes() != canonical:
            error(f"Runtime divergente do compose canônico: {path.relative_to(ROOT)}")


def validate_env() -> None:
    canonical = parse_env(ROOT / ".env.example")
    required = {
        "APP_VERSION", "VITE_APP_VERSION", "APP_SECRET_KEY", "FIELD_ENCRYPTION_KEY",
        "POSTGRES_PASSWORD", "POSTGRES_ADMIN_PASSWORD", "RABBITMQ_PASSWORD",
        "MINIO_ROOT_PASSWORD", "S3_SECRET_KEY", "CONTROL_PLANE_HOST", "API_HOST",
        "TENANT_DOMAIN_ROOT", "DOMAIN_RECONCILIATION_TOKEN", "BANKING_WEBHOOK_SECRET",
        "FINANCIAL_DATA_ROOT", "BACKEND_IMAGE", "FRONTEND_IMAGE", "GATEWAY_IMAGE",
    }
    missing = sorted(required - set(canonical))
    if missing:
        error(f"Variáveis obrigatórias ausentes no .env.example: {missing}")
    if canonical.get("APP_VERSION") or canonical.get("VITE_APP_VERSION"):
        error("APP_VERSION/VITE_APP_VERSION devem ficar vazios nos exemplos")
    if canonical.get("APP_PULL_POLICY") not in {"always", ""}:
        error("APP_PULL_POLICY canônico deve ser always")
    if canonical.get("FINANCIAL_DATA_ROOT") != ".":
        error("FINANCIAL_DATA_ROOT canônico deve ser .")
    for key, expected in {
        "BACKEND_IMAGE": "ghcr.io/wkarts/argws-financial-api:latest",
        "FRONTEND_IMAGE": "ghcr.io/wkarts/argws-financial-web:latest",
        "GATEWAY_IMAGE": "ghcr.io/wkarts/argws-financial-gateway:latest",
    }.items():
        if canonical.get(key) != expected:
            error(f"{key} canônico deve ser {expected}")

    env_paths = sorted((ROOT / "deployments").rglob(".env.example")) + [ROOT / "deployments/portainer/stack.env.example"]
    for path in env_paths:
        if path.is_file():
            parse_env(path)


def validate_versioning() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        error(f"VERSION inválida: {version!r}")
    METRICS["canonical_version"] = version
    frontend = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    if "version" in frontend:
        error("frontend/package.json não deve duplicar VERSION")
    for section in ("dependencies", "devDependencies"):
        for package, value in frontend.get(section, {}).items():
            if str(value).startswith(("^", "~", "*", ">", "<")):
                error(f"Dependência frontend não fixada: {package}={value}")
    if not (ROOT / "frontend/package-lock.json").is_file():
        warning("frontend/package-lock.json ausente; dependências são instaladas pelas versões diretas fixadas")
    backend_version = (ROOT / "backend/app/version.py").read_text(encoding="utf-8")
    vite = (ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    if 'os.getenv("APP_VERSION"' not in backend_version or '"VERSION"' not in backend_version:
        error("backend/app/version.py não resolve versão por ambiente/VERSION")
    if "../VERSION" not in vite or "VITE_APP_VERSION" not in vite:
        error("Vite não injeta VITE_APP_VERSION a partir de VERSION")


def validate_alembic() -> None:
    for filename, scope in (("alembic-platform.ini", "platform"), ("alembic-tenant.ini", "tenant")):
        path = ROOT / "backend" / filename
        text = path.read_text(encoding="utf-8")
        if f"script_location = %(here)s/migrations/{scope}" not in text:
            error(f"Alembic sem script_location portável: {path.relative_to(ROOT)}")
        if "prepend_sys_path = %(here)s" not in text:
            error(f"Alembic sem prepend_sys_path portável: {path.relative_to(ROOT)}")


def validate_workflows() -> None:
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^on:\s*$", text, re.MULTILINE):
            error(f"Workflow sem on: {path.relative_to(ROOT)}")
        if "jobs:" not in text:
            error(f"Workflow sem jobs: {path.relative_to(ROOT)}")


def validate_sensitive_files(allow_runtime_files: bool) -> None:
    if allow_runtime_files:
        return
    for relative in (".env", ".bootstrap-credentials.txt", "deployments/portainer/stack.env"):
        if (ROOT / relative).exists():
            error(f"Arquivo sensível não deve ser versionado/pacotado: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida ARGWS Financial Platform")
    parser.add_argument("--allow-runtime-files", action="store_true")
    args = parser.parse_args()
    required_files()
    validate_python()
    validate_shell()
    validate_compose()
    validate_env()
    validate_versioning()
    validate_alembic()
    validate_workflows()
    validate_sensitive_files(args.allow_runtime_files)
    report = {
        "status": "PASS" if not ERRORS else "FAIL",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "errors": ERRORS,
        "warnings": WARNINGS,
        "metrics": METRICS,
    }
    (ROOT / "VALIDATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
