#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
WARNINGS: list[str] = []
METRICS: dict[str, Any] = {}


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


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
        "compose.yaml", "compose.local-build.yaml", "backend/Dockerfile", "backend/app/version.py",
        "backend/app/preflight.py", "backend/app/domain_bootstrap.py", "backend/app/workers/celery_app.py",
        "frontend/Dockerfile", "frontend/vite.config.ts", "frontend/src/pages/LoginPage.vue",
        "frontend/src/stores/auth.ts", "scripts/generate_secrets.py", "scripts/package_release.py",
        "scripts/package_dockge_stack.py", "scripts/validate_dockge_runtime.py",
        "scripts/validate_runtime_contract.py", "scripts/validate_deployment_parity.py",
        "deployments/dockge/compose.yaml", "deployments/dockge/.env.example",
        "deployments/cloudpanel/compose.yaml", "deployments/cloudpanel/.env.example",
        "deployments/portainer/stack.yaml", "deployments/portainer/stack.env.example",
        "infrastructure/docker/gateway/Dockerfile", "infrastructure/nginx/gateway.conf.template",
        "infrastructure/docker/gateway/landing/index.html", ".github/workflows/ci.yml",
        ".github/workflows/publish.yml",
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


def validate_yaml() -> None:
    count = 0
    for path in sorted(ROOT.rglob("*.yaml")) + sorted(ROOT.rglob("*.yml")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        count += 1
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            error(f"YAML inválido: {path.relative_to(ROOT)}: {exc}")
    METRICS["yaml_files"] = count


def run_validator(relative: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        error(f"{relative} falhou: {detail}")


def validate_env_examples() -> None:
    root_env = parse_env(ROOT / ".env.example")
    if root_env.get("APP_VERSION") or root_env.get("VITE_APP_VERSION"):
        error("APP_VERSION/VITE_APP_VERSION devem ficar vazios no exemplo canônico")

    for path in sorted((ROOT / "deployments").rglob(".env.example")):
        parse_env(path)

    dockge = parse_env(ROOT / "deployments/dockge/.env.example")
    required = {
        "APP_NAME", "PLATFORM_DOMAIN", "CONTROL_PLANE_HOST", "ADMIN_HOST", "API_HOST", "DEMO_HOST",
        "TENANT_DOMAIN_ROOT", "FINANCIAL_DATA_ROOT", "POSTGRES_PASSWORD", "POSTGRES_ADMIN_PASSWORD",
        "RABBITMQ_PASSWORD", "S3_SECRET_KEY", "MINIO_ROOT_PASSWORD", "PLATFORM_ADMIN_PASSWORD",
        "DOMAIN_RECONCILIATION_TOKEN", "BANKING_WEBHOOK_SECRET", "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID", "ACME_DOMAIN", "CLOUDPANEL_SITE_DOMAIN", "CLOUDPANEL_WILDCARD_DOMAIN",
        "PROMETHEUS_ENABLED", "GRAFANA_ADMIN_PASSWORD",
    }
    missing = sorted(required - set(dockge))
    if missing:
        error(f"Exemplo Dockge incompleto: {missing}")
    if dockge.get("FINANCIAL_DATA_ROOT") != ".":
        error("FINANCIAL_DATA_ROOT do Dockge precisa ser .")
    expected = {
        "APP_NAME": "ARGWS Financial Platform",
        "PLATFORM_DOMAIN": "finance.argws.com.br",
        "CONTROL_PLANE_HOST": "control.finance.argws.com.br",
        "ADMIN_HOST": "admin.finance.argws.com.br",
        "API_HOST": "api.finance.argws.com.br",
        "DEMO_HOST": "demo.finance.argws.com.br",
        "TENANT_DOMAIN_ROOT": "finance.argws.com.br",
        "VITE_APP_NAME": "ARGWS Financial Platform",
    }
    for key, value in expected.items():
        if dockge.get(key) != value:
            error(f"Exemplo Dockge: {key} deve ser {value!r}")


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

    backend_version = (ROOT / "backend/app/version.py").read_text(encoding="utf-8")
    vite = (ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    if 'os.getenv("APP_VERSION"' not in backend_version or '"VERSION"' not in backend_version:
        error("backend/app/version.py não resolve versão por ambiente/VERSION")
    if "../VERSION" not in vite or "VITE_APP_VERSION" not in vite:
        error("Vite não injeta VITE_APP_VERSION a partir de VERSION")


def validate_product_copy() -> None:
    login = (ROOT / "frontend/src/pages/LoginPage.vue").read_text(encoding="utf-8")
    forbidden = {"FastAPI", "PostgreSQL", "Vue 3", "Python 3", "SaaS financeiro multitenant", "Isolamento por tenant"}
    leaked = sorted(term for term in forbidden if term.lower() in login.lower())
    if leaked:
        error(f"Login expõe tecnologia/arquitetura interna: {leaked}")
    for expected in ("Gestão financeira integrada", "Ambiente protegido"):
        if expected not in login:
            error(f"Login profissional sem texto esperado: {expected}")


def validate_celery_contract() -> None:
    text = (ROOT / "backend/app/workers/celery_app.py").read_text(encoding="utf-8")
    if "worker_enable_remote_control=False" not in text:
        error("Celery precisa manter remote control/pidbox desativado para RabbitMQ 4")
    if "worker_cancel_long_running_tasks_on_connection_loss=True" not in text:
        error("Celery precisa cancelar tarefas longas após perda de conexão")


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


def write_report() -> None:
    report = {
        "status": "PASS" if not ERRORS else "FAIL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "metrics": METRICS,
        "warnings": WARNINGS,
        "errors": ERRORS,
    }
    (ROOT / "VALIDATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Validation Report", "", f"Status: **{report['status']}**", "", "## Metrics",
        *[f"- {key}: {value}" for key, value in sorted(METRICS.items())], "", "## Warnings",
        *([f"- {item}" for item in WARNINGS] or ["- Nenhum"]), "", "## Errors",
        *([f"- {item}" for item in ERRORS] or ["- Nenhum"]), "",
    ]
    (ROOT / "VALIDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida ARGWS Financial Platform")
    parser.add_argument("--allow-runtime-files", action="store_true")
    args = parser.parse_args()
    required_files()
    validate_python()
    validate_shell()
    validate_yaml()
    validate_env_examples()
    validate_versioning()
    validate_product_copy()
    validate_celery_contract()
    validate_alembic()
    validate_workflows()
    validate_sensitive_files(args.allow_runtime_files)
    run_validator("scripts/validate_runtime_contract.py")
    run_validator("scripts/validate_dockge_runtime.py")
    write_report()
    if ERRORS:
        for item in ERRORS:
            print(f"[ERRO] {item}")
        return 1
    for item in WARNINGS:
        print(f"[AVISO] {item}")
    print("Validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
