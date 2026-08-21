#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
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


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


def project_files() -> list[Path]:
    ignored = {
        ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        "dist", "financial-data", ".releases", "release-artifacts",
    }
    return [p for p in ROOT.rglob("*") if p.is_file() and not any(part in ignored for part in p.parts)]


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def env_duplicate_keys(path: Path) -> list[str]:
    keys: list[str] = []
    if not path.is_file():
        return []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.append(line.split("=", 1)[0].strip())
    return sorted({key for key in keys if keys.count(key) > 1})


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"YAML inválido em {path.relative_to(ROOT)}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def check_required_files() -> None:
    required = [
        "README.md", "DELIVERY_INDEX.md", "LICENSE", "SECURITY.md", "VERSION", "CHANGELOG.md", "RELEASE_NOTES.md",
        "PR_TITLE.md", "PR_DESCRIPTION.md", ".env.example", "compose.yaml", "Makefile",
        "backend/Dockerfile", "backend/app/version.py", "frontend/Dockerfile", "backend/alembic-platform.ini", "backend/alembic-tenant.ini",
        "infrastructure/nginx/gateway.conf", "infrastructure/docker/gateway/Dockerfile",
        "infrastructure/backup/rclone.conf.example", "secrets/backup-age-identity.txt.example",
        "scripts/deploy_cloudpanel_dockge.sh", "scripts/install_local.sh", "scripts/backup.sh", "scripts/restore.sh",
        "scripts/generate_secrets.py", "scripts/portainer_deploy.py", "scripts/package_release.py", "scripts/deploy/lib.sh",
        "deployments/docker/compose.images.yaml", "deployments/docker/install.sh", "deployments/docker/.env.example",
        "deployments/dockge/compose.yaml", "deployments/dockge/install.sh", "deployments/dockge/.env.example",
        "deployments/cloudpanel/compose.yaml", "deployments/cloudpanel/install.sh", "deployments/cloudpanel/.env.example",
        "deployments/portainer/stack.yaml", "deployments/portainer/stack-build.yaml", "deployments/portainer/deploy.sh", "deployments/portainer/.env.example",
        "docs/architecture/ARCHITECTURE.md", "docs/architecture/FLOWS.md", "docs/security/TENANT_ISOLATION.md",
        "docs/operations/DEPLOY_DOCKGE.md", "docs/operations/DEPLOY_CLOUDPANEL.md", "docs/operations/DEPLOY_PORTAINER.md",
        "docs/operations/BACKUP_RESTORE.md", "docs/operations/DOMAINS_SSL.md",
        "docs/integrations/SMTP_EVOLUTION.md", "docs/integrations/BANKING_CNAB.md",
        "docs/product/COMPLETION_MATRIX.md", "docs/release/DELIVERY_REPORT.md", "docs/API.md", "docs/ACCEPTANCE_CHECKLIST.md",
        ".github/workflows/ci.yml", ".github/workflows/publish.yml",
    ]
    for item in required:
        if not (ROOT / item).is_file():
            error(f"Arquivo obrigatório ausente: {item}")


def check_python() -> None:
    paths = sorted((ROOT / "backend").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py"))
    for path in paths:
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
                modules = [i.name for i in node.names if i.name == "app" or i.name.startswith("app.")]
            elif isinstance(node, ast.ImportFrom) and node.module and (node.module == "app" or node.module.startswith("app.")):
                modules = [node.module]
            for module in modules:
                if not _module_exists(module):
                    error(f"Import interno inexistente: {path.relative_to(ROOT)} -> {module}")


def check_settings_contract() -> None:
    config_path = ROOT / "backend/app/core/config.py"
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
    for path in sorted((ROOT / "backend/app").rglob("*.py")):
        source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports_global_settings = any(
            isinstance(n, ast.ImportFrom) and n.module == "app.core.config" and any(a.name == "settings" for a in n.names)
            for n in ast.walk(source)
        )
        if not imports_global_settings:
            continue
        for node in ast.walk(source):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "settings":
                used.add(node.attr)
    missing = sorted(used - defined)
    if missing:
        error(f"Atributos settings usados mas não definidos: {missing}")


def check_shell() -> None:
    bash = shutil.which("bash")
    if bash is None:
        warning("bash indisponível; scripts shell não foram validados")
        return
    count = 0
    for path in sorted(ROOT.rglob("*.sh")):
        if any(part in {".git", "node_modules", "financial-data"} for part in path.parts):
            continue
        count += 1
        result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, check=False)
        if result.returncode:
            error(f"Shell inválido: {path.relative_to(ROOT)}: {result.stderr.strip()}")
    METRICS["shell_scripts"] = count


def check_compose_file(path: Path, env_path: Path, expected_services: set[str], expected_queues: set[str]) -> None:
    data = load_yaml(path)
    services_data = data.get("services", {}) if isinstance(data.get("services"), dict) else {}
    services = set(services_data)
    missing = expected_services - services
    if missing:
        error(f"Serviços ausentes em {path.relative_to(ROOT)}: {sorted(missing)}")
    commands = "\n".join(str(s.get("command", "")) for s in services_data.values() if isinstance(s, dict))
    for queue in sorted(expected_queues):
        if queue not in commands:
            error(f"Fila Celery ausente em {path.relative_to(ROOT)}: {queue}")
    env_keys = set(parse_env(env_path))
    referenced = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", path.read_text(encoding="utf-8")))
    missing_env = sorted(referenced - env_keys)
    if missing_env:
        error(f"Variáveis de {path.relative_to(ROOT)} ausentes em {env_path.relative_to(ROOT)}: {missing_env}")


def check_compose() -> None:
    source_services = {
        "financial-storage-init", "financial-postgres", "financial-redis", "financial-rabbitmq", "financial-minio",
        "financial-minio-init", "financial-migrate", "financial-migrate-tenants", "financial-bootstrap", "financial-api",
        "financial-worker-default", "financial-worker-billing", "financial-worker-notifications", "financial-worker-backups",
        "financial-beat", "financial-web", "financial-gateway", "financial-api-test", "financial-web-test",
    }
    image_services = source_services - {"financial-storage-init", "financial-api-test", "financial-web-test"}
    queues = {
        "financial.default", "financial.provisioning", "financial.outbox", "financial.billing", "financial.banking",
        "financial.cnab", "financial.reconciliation", "financial.notifications", "financial.webhooks", "financial.backups", "financial.exports",
    }
    check_compose_file(ROOT / "compose.yaml", ROOT / ".env.example", source_services, queues)
    check_compose_file(ROOT / "deployments/docker/compose.images.yaml", ROOT / "deployments/docker/.env.example", image_services, queues)
    check_compose_file(ROOT / "deployments/dockge/compose.yaml", ROOT / "deployments/dockge/.env.example", image_services, queues)
    check_compose_file(ROOT / "deployments/portainer/stack.yaml", ROOT / "deployments/portainer/.env.example", image_services, queues)

    canonical = (ROOT / "compose.yaml").read_bytes()
    cloudpanel = ROOT / "deployments/cloudpanel/compose.yaml"
    if cloudpanel.read_bytes() != canonical:
        error(f"Compose divergente do canônico: {cloudpanel.relative_to(ROOT)}")

    dockge_text = (ROOT / "deployments/dockge/compose.yaml").read_text(encoding="utf-8")
    if re.search(r"^\s+build:\s*$", dockge_text, re.MULTILINE):
        error("A stack Dockge não pode depender de build local")
    if "GATEWAY_IMAGE" not in dockge_text:
        error("Stack Dockge não referencia a imagem publicada do gateway")
    if "ghcr.io/wkarts/argws-financial-api:latest" not in dockge_text:
        error("Stack Dockge não possui fallback GHCR latest para a API")
    if re.search(r"^\s+APP_VERSION:\s*", dockge_text, re.MULTILINE):
        error("Stack Dockge não deve sobrescrever a versão embutida nas imagens")

    portainer_text = (ROOT / "deployments/portainer/stack.yaml").read_text(encoding="utf-8")
    if re.search(r"^\s+build:\s*$", portainer_text, re.MULTILINE):
        error("A stack Portainer de imagens não pode depender de build local")
    if "GATEWAY_IMAGE" not in portainer_text:
        error("Stack Portainer não referencia a imagem do gateway")


def check_yaml_files() -> None:
    count = 0
    for path in sorted(ROOT.rglob("*.yml")) + sorted(ROOT.rglob("*.yaml")):
        if any(part in {".git", "node_modules", "financial-data"} for part in path.parts):
            continue
        load_yaml(path)
        count += 1
    METRICS["yaml_files"] = count


def check_workflows() -> None:
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^on:\s*$", text, re.MULTILINE):
            error(f"Workflow sem gatilho `on`: {path.relative_to(ROOT)}")
        if "jobs:" not in text:
            error(f"Workflow sem jobs: {path.relative_to(ROOT)}")


def check_frontend_manifest() -> None:
    data = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    if "version" in data:
        error("frontend/package.json não deve duplicar a versão da aplicação; use VERSION")
    for section in ("dependencies", "devDependencies"):
        for package, version in data.get(section, {}).items():
            if str(version).startswith(("^", "~", "*", ">", "<")):
                error(f"Dependência frontend não fixada: {package}={version}")
    required_scripts = {"build", "test:run", "typecheck"}
    missing = required_scripts - set(data.get("scripts", {}))
    if missing:
        error(f"Scripts frontend ausentes: {sorted(missing)}")
    if not (ROOT / "frontend/package-lock.json").is_file():
        warning("frontend/package-lock.json não está incluído; o Dockerfile usa npm install com versões diretas fixadas")


def check_vue_imports() -> None:
    source_root = ROOT / "frontend/src"
    vue_count = 0
    for path in sorted(source_root.rglob("*")):
        if path.suffix not in {".ts", ".vue"}:
            continue
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"(?:from\s+|import\s*)['\"](\.{1,2}/[^'\"]+)['\"]", content):
            candidate = (path.parent / target).resolve()
            choices = [candidate, candidate.with_suffix(".ts"), candidate.with_suffix(".vue"), candidate / "index.ts"]
            if not any(item.exists() for item in choices):
                error(f"Import frontend não encontrado: {path.relative_to(ROOT)} -> {target}")
        if path.suffix == ".vue":
            vue_count += 1
            if "<template" not in content or "</template>" not in content:
                error(f"Componente Vue sem template completo: {path.relative_to(ROOT)}")
            if content.count("<template") != content.count("</template>"):
                error(f"Templates Vue desbalanceados: {path.relative_to(ROOT)}")
    METRICS["vue_files"] = vue_count


def check_frontend_surface() -> None:
    required_pages = {
        "ControlDashboardPage.vue", "TenantsPage.vue", "TenantDetailPage.vue", "PlansPage.vue", "PlatformUsersPage.vue",
        "ProvisioningPage.vue", "BackupsPage.vue", "ControlAuditPage.vue", "ControlSettingsPage.vue", "PlatformAccessPage.vue",
        "TenantDashboardPage.vue", "CompaniesPage.vue", "CustomersPage.vue", "ServicesPage.vue",
        "ContractsPage.vue", "ReceivablesPage.vue", "ChargesPage.vue", "PaymentsPage.vue", "PixAutomaticPage.vue",
        "ReconciliationPage.vue", "NegotiationsPage.vue", "BankingPage.vue", "FiscalDocumentsPage.vue", "NotificationsPage.vue",
        "IntegrationsPage.vue", "DeveloperIntegrationsPage.vue", "DocumentsPage.vue", "ImportsPage.vue", "UsersPage.vue", "AuditPage.vue",
        "PublicPaymentPage.vue",
    }
    existing = {p.name for p in (ROOT / "frontend/src/pages").glob("*.vue")}
    missing = required_pages - existing
    if missing:
        error(f"Telas obrigatórias ausentes: {sorted(missing)}")


def check_env() -> None:
    env_paths = [
        ROOT / ".env.example",
        ROOT / "deployments/development/.env.example",
        ROOT / "deployments/staging/.env.example",
        ROOT / "deployments/production/.env.example",
        ROOT / "deployments/docker/.env.example",
        ROOT / "deployments/dockge/.env.example",
        ROOT / "deployments/cloudpanel/.env.example",
        ROOT / "deployments/portainer/.env.example",
        ROOT / "deployments/portainer/stack.env.example",
    ]
    for path in env_paths:
        duplicates = env_duplicate_keys(path)
        if duplicates:
            error(f"Variáveis duplicadas em {path.relative_to(ROOT)}: {duplicates}")

    canonical = parse_env(ROOT / ".env.example")
    required = {
        "APP_VERSION", "VITE_APP_VERSION", "APP_SECRET_KEY", "FIELD_ENCRYPTION_KEY", "POSTGRES_PASSWORD",
        "RABBITMQ_PASSWORD", "MINIO_ROOT_PASSWORD", "S3_SECRET_KEY", "CONTROL_PLANE_HOST", "API_HOST",
        "TENANT_DOMAIN_ROOT", "DOMAIN_RECONCILIATION_TOKEN", "EVOLUTION_WEBHOOK_SECRET", "BANKING_WEBHOOK_SECRET",
        "RATE_LIMIT_DEFAULT", "FINANCIAL_DATA_ROOT", "BACKEND_IMAGE", "FRONTEND_IMAGE", "GATEWAY_IMAGE",
        "ACME_IMAGE", "CLOUDPANEL_AGENT_IMAGE", "RCLONE_CONFIG_PATH", "BACKUP_AGE_IDENTITY_PATH",
    }
    missing = required - set(canonical)
    if missing:
        error(f"Variáveis obrigatórias ausentes no .env.example: {sorted(missing)}")
    if canonical.get("BOOTSTRAP_DEMO_TENANT", "").lower() != "false":
        error("BOOTSTRAP_DEMO_TENANT deve vir desabilitado no ambiente de produção")
    if canonical.get("APP_VERSION") or canonical.get("VITE_APP_VERSION"):
        error("APP_VERSION e VITE_APP_VERSION devem ficar vazios nos exemplos; os scripts leem VERSION")

    canonical_keys = set(canonical)
    image_keys = {"BACKEND_IMAGE", "FRONTEND_IMAGE", "GATEWAY_IMAGE", "ACME_IMAGE", "CLOUDPANEL_AGENT_IMAGE"}
    for path in env_paths[1:]:
        values = parse_env(path)
        if values.get("APP_VERSION") != canonical.get("APP_VERSION"):
            error(f"APP_VERSION deve ser automática em {path.relative_to(ROOT)}")
        if values.get("VITE_APP_VERSION") != canonical.get("VITE_APP_VERSION"):
            error(f"VITE_APP_VERSION deve ser automática em {path.relative_to(ROOT)}")
        missing_keys = sorted(canonical_keys - set(values))
        if missing_keys:
            error(f"Variáveis canônicas ausentes em {path.relative_to(ROOT)}: {missing_keys}")
        for key in image_keys:
            value = values.get(key, "")
            if value and not value.endswith(":latest"):
                error(f"Imagem do produto deve usar :latest em {path.relative_to(ROOT)}: {key}={value}")
    for key in image_keys:
        value = canonical.get(key, "")
        if value and not value.endswith(":latest"):
            error(f"Imagem do produto deve usar :latest no .env.example: {key}={value}")


def check_migrations() -> None:
    for scope in ("platform", "tenant"):
        versions = [p for p in (ROOT / f"backend/migrations/{scope}/versions").glob("*.py") if p.name != "__init__.py"]
        if not versions:
            error(f"Nenhuma migration encontrada para {scope}")
        revisions: set[str] = set()
        for path in versions:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            revision = None
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "revision" and isinstance(node.value, ast.Constant):
                            revision = str(node.value.value)
            if not revision:
                error(f"Migration sem revision: {path.relative_to(ROOT)}")
            elif revision in revisions:
                error(f"Revision duplicada em {scope}: {revision}")
            revisions.add(revision or "")
        METRICS[f"{scope}_migrations"] = len(versions)


def check_versions() -> None:
    canonical = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", canonical):
        error(f"VERSION inválida: {canonical!r}")

    init_text = (ROOT / "backend/app/__init__.py").read_text(encoding="utf-8")
    config_text = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    version_text = (ROOT / "backend/app/version.py").read_text(encoding="utf-8")
    vite_text = (ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    docker_backend = (ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
    docker_frontend = (ROOT / "frontend/Dockerfile").read_text(encoding="utf-8")

    if "get_app_version()" not in init_text:
        error("backend/app/__init__.py não resolve a versão pela fonte canônica")
    if "app_version: str = get_app_version()" not in config_text:
        error("Settings.app_version não resolve a versão pela fonte canônica")
    if 'os.getenv("APP_VERSION"' not in version_text or '"VERSION"' not in version_text:
        error("backend/app/version.py não implementa resolução de versão por ambiente/VERSION")
    if "../VERSION" not in vite_text or "VITE_APP_VERSION" not in vite_text:
        error("Vite não injeta VITE_APP_VERSION a partir de VERSION")
    if "COPY VERSION" not in docker_backend or "COPY VERSION" not in docker_frontend:
        error("Dockerfiles precisam empacotar o arquivo VERSION")

    operational_paths = [
        ROOT / "backend/app/__init__.py",
        ROOT / "backend/app/core/config.py",
        ROOT / "frontend/package.json",
        ROOT / "frontend/Dockerfile",
        ROOT / "frontend/vite.config.ts",
        ROOT / ".env.example",
        ROOT / "compose.yaml",
        ROOT / "deployments/docker/compose.images.yaml",
        ROOT / "deployments/portainer/stack.yaml",
        ROOT / "deployments/portainer/stack-build.yaml",
        ROOT / "deployments/docker/install.sh",
        ROOT / "deployments/portainer/deploy.sh",
    ]
    for path in operational_paths:
        if canonical and canonical in path.read_text(encoding="utf-8"):
            error(f"Versão canônica duplicada em arquivo operacional: {path.relative_to(ROOT)}")

    METRICS["canonical_version"] = canonical


def check_runtime_imports_and_routes() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["APP_ENV"] = "testing"
    mapper_code = "from sqlalchemy.orm import configure_mappers; import app.models.platform, app.models.tenant; configure_mappers(); print('OK')"
    result = subprocess.run([sys.executable, "-c", mapper_code], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        error(f"Mapeamentos SQLAlchemy falharam: {(result.stderr or result.stdout).strip()}")

    route_count = 0
    seen: set[tuple[str, str, str]] = set()
    for path in sorted((ROOT / "backend/app/api/routes").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                    continue
                method = deco.func.attr.upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not deco.args:
                    continue
                arg = deco.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    continue
                key = (path.name, method, arg.value)
                if key in seen:
                    error(f"Rota duplicada no mesmo módulo: {path.relative_to(ROOT)} {method} {arg.value}")
                seen.add(key)
                route_count += 1
    METRICS["fastapi_route_decorators"] = route_count


def check_alembic_configs() -> None:
    for filename, scope in (("alembic-platform.ini", "platform"), ("alembic-tenant.ini", "tenant")):
        path = ROOT / "backend" / filename
        content = path.read_text(encoding="utf-8")
        expected = f"script_location = %(here)s/migrations/{scope}"
        if expected not in content:
            error(f"Alembic não usa caminho portável em {path.relative_to(ROOT)}")
        if "prepend_sys_path = %(here)s" not in content:
            error(f"Alembic não usa prepend_sys_path portável em {path.relative_to(ROOT)}")


def _backend_api_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "backend/app/api/routes").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        prefix = ""
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
                continue
            for keyword in node.value.keywords:
                if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                    prefix = str(keyword.value.value)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr.upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not decorator.args:
                    continue
                route_arg = decorator.args[0]
                if isinstance(route_arg, ast.Constant) and isinstance(route_arg.value, str):
                    routes.add((method, prefix + route_arg.value))
    return routes


def _route_matches(frontend_path: str, backend_path: str) -> bool:
    frontend_path = frontend_path.split("?", 1)[0]
    if backend_path.startswith("/api"):
        backend_path = backend_path[4:]
    frontend_parts = frontend_path.strip("/").split("/")
    backend_parts = backend_path.strip("/").split("/")
    if len(frontend_parts) != len(backend_parts):
        return False
    return all(
        left == right or left.startswith("{") or right.startswith("{")
        for left, right in zip(frontend_parts, backend_parts, strict=True)
    )


def check_frontend_api_contract() -> None:
    backend_routes = _backend_api_routes()
    call_pattern = re.compile(
        r"\bapi\.(get|post|put|patch|delete)(?:<[^\n(]+>)?\s*\(\s*([`'\"])(.*?)\2",
        re.DOTALL,
    )
    calls: list[tuple[str, str, Path]] = []
    for path in sorted((ROOT / "frontend/src").rglob("*")):
        if path.suffix not in {".ts", ".vue"}:
            continue
        content = path.read_text(encoding="utf-8")
        for match in call_pattern.finditer(content):
            endpoint = re.sub(r"\$\{[^}]+\}", "{param}", match.group(3))
            calls.append((match.group(1).upper(), endpoint, path))
    missing = [
        (method, endpoint, path)
        for method, endpoint, path in calls
        if not any(
            method == backend_method and _route_matches(endpoint, backend_path)
            for backend_method, backend_path in backend_routes
        )
    ]
    for method, endpoint, path in missing:
        error(f"Chamada frontend sem rota backend: {path.relative_to(ROOT)} {method} {endpoint}")
    METRICS["frontend_api_calls"] = len(calls)
    METRICS["frontend_api_contracts"] = len({(method, endpoint) for method, endpoint, _ in calls})
    METRICS["frontend_api_contract_mismatches"] = len(missing)


def check_sensitive_files(*, allow_runtime_files: bool) -> None:
    if allow_runtime_files:
        return
    explicit_runtime = [
        ROOT / ".env",
        ROOT / ".bootstrap-credentials.txt",
        ROOT / "deployments/portainer/stack.env",
        ROOT / "deployments/portainer/.bootstrap-credentials.txt",
    ]
    for path in explicit_runtime:
        if path.exists():
            error(f"Arquivo sensível não deve compor o pacote: {path.relative_to(ROOT)}")
    for path in project_files():
        if path.name in {"rclone.conf", "backup-age-identity.txt", ".bootstrap-credentials.txt"} and ".example" not in path.name:
            error(f"Secret real potencialmente versionado: {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida a ARGWS Financial Platform")
    parser.add_argument("--allow-runtime-files", action="store_true")
    args = parser.parse_args()
    check_required_files()
    check_python()
    check_internal_python_imports()
    check_settings_contract()
    check_shell()
    check_yaml_files()
    check_compose()
    check_workflows()
    check_frontend_manifest()
    check_vue_imports()
    check_frontend_surface()
    check_env()
    check_migrations()
    check_alembic_configs()
    check_versions()
    check_runtime_imports_and_routes()
    check_frontend_api_contract()
    check_sensitive_files(allow_runtime_files=args.allow_runtime_files)
    files = project_files()
    report = {
        "status": "PASS" if not ERRORS else "FAIL",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "errors": ERRORS,
        "warnings": WARNINGS,
        "metrics": {
            **METRICS,
            "python_files": len([p for p in files if p.suffix == ".py"]),
            "documentation_files": len([p for p in files if p.suffix == ".md"]),
            "total_files": len(files),
        },
    }
    (ROOT / "VALIDATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
