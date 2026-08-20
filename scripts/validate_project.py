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


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


def project_files() -> list[Path]:
    ignored = {".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in ignored for part in path.parts)
    ]


def check_required_files() -> None:
    required = [
        "README.md",
        "LICENSE",
        "VERSION",
        ".env.example",
        "compose.yaml",
        "backend/Dockerfile",
        "frontend/Dockerfile",
        "backend/alembic-platform.ini",
        "backend/alembic-tenant.ini",
        "infrastructure/nginx/gateway.conf",
        "infrastructure/backup/rclone.conf.example",
        "scripts/deploy_cloudpanel_dockge.sh",
        "scripts/backup.sh",
        "scripts/restore.sh",
        "scripts/generate_secrets.py",
        "docs/architecture/ARCHITECTURE.md",
        "docs/architecture/FLOWS.md",
        "docs/security/TENANT_ISOLATION.md",
        "docs/operations/DEPLOY_CLOUDPANEL_DOCKGE.md",
        "docs/operations/DOMAINS_SSL.md",
        "docs/operations/BACKUP_RESTORE.md",
        "docs/integrations/SMTP_EVOLUTION.md",
        "docs/integrations/BANKING_CNAB.md",
        "docs/LEGACY_IMPORT.md",
        "docs/API.md",
        "docs/ACCEPTANCE_CHECKLIST.md",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    ]
    for item in required:
        if not (ROOT / item).is_file():
            error(f"Arquivo obrigatório ausente: {item}")


def check_python() -> None:
    for path in sorted((ROOT / "backend").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            error(f"Python inválido: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")


def _module_exists(module: str) -> bool:
    relative = Path(*module.split("."))
    backend = ROOT / "backend"
    return (backend / relative).with_suffix(".py").is_file() or (backend / relative / "__init__.py").is_file()


def check_internal_python_imports() -> None:
    for path in sorted((ROOT / "backend" / "app").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names if item.name == "app" or item.name.startswith("app.")]
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "app" or node.module.startswith("app."):
                    modules = [node.module]
            for module in modules:
                if not _module_exists(module):
                    error(f"Import interno inexistente: {path.relative_to(ROOT)} -> {module}")


def check_settings_contract() -> None:
    config_path = ROOT / "backend" / "app" / "core" / "config.py"
    tree = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    defined: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    defined.add(item.target.id)
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined.add(item.name)
    used: set[str] = set()
    for path in sorted((ROOT / "backend" / "app").rglob("*.py")):
        source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(source):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "settings":
                used.add(node.attr)
    missing = sorted(used - defined)
    if missing:
        error(f"Atributos settings usados mas não definidos: {missing}")


def check_shell() -> None:
    bash = shutil.which("bash")
    if bash is None:
        warning("bash indisponível; scripts shell não foram validados.")
        return
    for path in sorted((ROOT / "scripts").glob("*.sh")):
        result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error(f"Shell inválido: {path.relative_to(ROOT)}: {result.stderr.strip()}")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        error(f"YAML inválido em {path.relative_to(ROOT)}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def check_compose() -> None:
    path = ROOT / "compose.yaml"
    data = load_yaml(path)
    expected = {
        "financial-postgres",
        "financial-redis",
        "financial-rabbitmq",
        "financial-minio",
        "financial-minio-init",
        "financial-migrate",
        "financial-init",
        "financial-api",
        "financial-worker",
        "financial-beat",
        "financial-web",
        "financial-gateway",
        "financial-api-test",
        "financial-web-test",
    }
    services = set(data.get("services", {}))
    missing = expected - services
    if missing:
        error(f"Serviços ausentes no Compose: {sorted(missing)}")
    worker = str(data.get("services", {}).get("financial-worker", {}).get("command", []))
    for queue in (
        "financial.provisioning",
        "financial.billing",
        "financial.outbox",
        "financial.notifications",
        "financial.backups",
    ):
        if queue not in worker:
            error(f"Fila Celery ausente no worker do Compose: {queue}")
    env_keys = set(parse_env(ROOT / ".env.example"))
    compose_text = path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", compose_text))
    missing_env = sorted(referenced - env_keys)
    if missing_env:
        error(f"Variáveis do Compose ausentes no .env.example: {missing_env}")


def check_workflows() -> None:
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        data = load_yaml(path)
        if not data:
            continue
        # PyYAML 1.1 pode interpretar `on` como boolean; a existência textual é o requisito aqui.
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^on:\s*$", text, re.MULTILINE):
            error(f"Workflow sem gatilho `on`: {path.relative_to(ROOT)}")
        if "jobs:" not in text:
            error(f"Workflow sem jobs: {path.relative_to(ROOT)}")


def check_frontend_manifest() -> None:
    data = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    for section in ("dependencies", "devDependencies"):
        for package, version in data.get(section, {}).items():
            if str(version).startswith(("^", "~", "*", ">", "<")):
                error(f"Dependência frontend não fixada: {package}={version}")


def check_vue_imports() -> None:
    source_root = ROOT / "frontend" / "src"
    for path in sorted(source_root.rglob("*")):
        if path.suffix not in {".ts", ".vue"}:
            continue
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"(?:from\s+|import\s*)['\"](\.{1,2}/[^'\"]+)['\"]", content):
            candidate = (path.parent / target).resolve()
            choices = [candidate, candidate.with_suffix(".ts"), candidate.with_suffix(".vue"), candidate / "index.ts"]
            if not any(item.exists() for item in choices):
                error(f"Import frontend não encontrado: {path.relative_to(ROOT)} -> {target}")
        if path.suffix == ".vue" and ("<template" not in content or "</template>" not in content):
            error(f"Componente Vue sem template completo: {path.relative_to(ROOT)}")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def check_env() -> None:
    values = parse_env(ROOT / ".env.example")
    required = [
        "APP_SECRET_KEY",
        "FIELD_ENCRYPTION_KEY",
        "POSTGRES_PASSWORD",
        "RABBITMQ_PASSWORD",
        "MINIO_ROOT_PASSWORD",
        "S3_SECRET_KEY",
        "CONTROL_PLANE_HOST",
        "TENANT_DOMAIN_ROOT",
        "DOMAIN_RECONCILIATION_TOKEN",
        "RATE_LIMIT_DEFAULT",
    ]
    for key in required:
        if key not in values:
            error(f"Variável obrigatória ausente no .env.example: {key}")
    if values.get("BOOTSTRAP_DEMO_TENANT", "").lower() != "false":
        error("BOOTSTRAP_DEMO_TENANT deve vir desabilitado no .env.example de produção.")


def check_migrations() -> None:
    for scope in ("platform", "tenant"):
        versions = [
            path
            for path in (ROOT / "backend" / "migrations" / scope / "versions").glob("*.py")
            if path.name != "__init__.py"
        ]
        if not versions:
            error(f"Nenhuma migration encontrada para {scope}")


def check_versions() -> None:
    canonical = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    init_text = (ROOT / "backend" / "app" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)', init_text)
    frontend = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))["version"]
    env_version = parse_env(ROOT / ".env.example").get("APP_VERSION")
    observed = {
        "backend/app/__init__.py": match.group(1) if match else None,
        "frontend/package.json": frontend,
        ".env.example": env_version,
    }
    for source, value in observed.items():
        if value != canonical:
            error(f"Versão divergente em {source}: {value!r}; esperado {canonical!r}")


def check_sensitive_files(*, allow_runtime_files: bool = False) -> None:
    if allow_runtime_files:
        return
    forbidden = [ROOT / ".env", ROOT / ".bootstrap-credentials.txt"]
    for path in forbidden:
        if path.exists():
            error(f"Arquivo sensível não deve compor o pacote: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida a estrutura da ARGWS Financial Platform.")
    parser.add_argument(
        "--allow-runtime-files",
        action="store_true",
        help="Permite .env e .bootstrap-credentials.txt em uma stack já provisionada.",
    )
    args = parser.parse_args()
    check_required_files()
    check_python()
    check_internal_python_imports()
    check_settings_contract()
    check_shell()
    check_compose()
    check_workflows()
    check_frontend_manifest()
    check_vue_imports()
    check_env()
    check_migrations()
    check_versions()
    check_sensitive_files(allow_runtime_files=args.allow_runtime_files)

    files = project_files()
    report = {
        "status": "PASS" if not ERRORS else "FAIL",
        "errors": ERRORS,
        "warnings": WARNINGS,
        "python_files": len([p for p in files if p.suffix == ".py"]),
        "vue_files": len([p for p in files if p.suffix == ".vue"]),
        "documentation_files": len([p for p in files if p.suffix == ".md"]),
        "total_files": len(files),
    }
    output = ROOT / "VALIDATION_REPORT.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
