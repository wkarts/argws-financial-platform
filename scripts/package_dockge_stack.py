#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_DIRS = (
    "data-postgres",
    "data-redis",
    "data-rabbitmq",
    "data-minio",
    "data-backups",
    "data-runtime",
    "data-celery",
    "data-prometheus",
    "data-grafana",
    "data-monitoring",
    "data-acme",
    "data-certs",
    "data-cloudpanel-agent",
)


class NoAliasDumper(yaml.SafeDumper):
    """Dumper sem anchors/aliases para compatibilidade com o editor do Dockge."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_alias_free_yaml(text: str) -> None:
    """Falha somente quando existe sintaxe YAML real de anchor, alias ou merge."""

    try:
        tokens = list(yaml.scan(text))
    except yaml.YAMLError as exc:
        raise SystemExit(f"Render Dockge gerou YAML inválido: {exc}") from exc

    for token in tokens:
        if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)):
            raise SystemExit("Render Dockge ainda contém YAML anchor/alias")
        if isinstance(token, yaml.tokens.ScalarToken) and token.value == "<<":
            raise SystemExit("Render Dockge ainda contém YAML merge key")


def render_dockge_compose(source: Path) -> str:
    """Expande aliases e entrega um Compose plano e completo para o Dockge."""

    raw = source.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SystemExit(f"Compose Dockge de origem inválido: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
        raise SystemExit("Compose Dockge inválido ou sem services")

    # As extensões x-* são úteis no fonte, mas não podem permanecer no artefato
    # consumido pelo editor YAML do Dockge. O safe_load já resolveu os merges.
    for key in list(data):
        if isinstance(key, str) and key.startswith("x-"):
            data.pop(key, None)

    # O preflight precisa auditar o ambiente efetivamente configurado pelo
    # operador, inclusive as variáveis específicas do perfil CloudPanel/ACME.
    # No fonte canônico várias variáveis são selecionadas no bloco x-api-env;
    # no pacote Dockge carregamos também o .env completo. As chaves declaradas
    # em `environment` continuam tendo precedência, conforme a especificação do
    # Docker Compose, e as demais (ACME_DOMAIN, ACME_EMAIL, CLOUDPANEL_*) ficam
    # disponíveis ao validador sem duplicação manual no YAML.
    preflight = data["services"].get("financial-preflight")
    if not isinstance(preflight, dict):
        raise SystemExit("Compose Dockge sem financial-preflight")
    preflight["env_file"] = [".env"]

    rendered = yaml.dump(
        data,
        Dumper=NoAliasDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100000,
    )
    rendered = (
        "# ARGWS Financial Platform — Dockge/CloudPanel, produção por imagens.\n"
        "# YAML plano, sem recursos de reutilização que excedam limites do parser do Dockge.\n"
        "# O financial-preflight lê também o .env completo para validar o perfil CloudPanel/ACME.\n\n"
        + rendered
    )

    assert_alias_free_yaml(rendered)

    parsed = yaml.safe_load(rendered)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("services"), dict):
        raise SystemExit("Render Dockge perdeu a seção services")
    if set(parsed["services"]) != set(data["services"]):
        raise SystemExit("Render Dockge alterou a lista de serviços")

    packaged_preflight = parsed["services"].get("financial-preflight") or {}
    env_files = packaged_preflight.get("env_file") or []
    if ".env" not in env_files:
        raise SystemExit("Render Dockge não entrega o .env completo ao financial-preflight")

    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Empacota a stack Dockge/CloudPanel image-only pronta para extração."
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent)
    args = parser.parse_args()

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("VERSION vazia")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"ARGWS-Financial-Platform-v{version}-Dockge.zip"
    archive.unlink(missing_ok=True)

    compose = ROOT / "deployments/dockge/compose.yaml"
    env_example = ROOT / "deployments/dockge/.env.example"
    readme = ROOT / "deployments/dockge/README.md"
    for path in (compose, env_example, readme):
        if not path.is_file():
            raise SystemExit(f"Arquivo Dockge ausente: {path.relative_to(ROOT)}")

    compose_text = compose.read_text(encoding="utf-8")
    if "build:" in compose_text or "dockerfile:" in compose_text:
        raise SystemExit("Compose Dockge ainda contém build local")

    for image in (
        "ghcr.io/wkarts/argws-financial-api:latest",
        "ghcr.io/wkarts/argws-financial-web:latest",
        "ghcr.io/wkarts/argws-financial-gateway:latest",
        "ghcr.io/wkarts/argws-financial-acme:latest",
        "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest",
    ):
        if image not in compose_text:
            raise SystemExit(f"Compose Dockge não usa imagem esperada: {image}")

    for service in (
        "financial-preflight",
        "financial-domain-init",
        "financial-prometheus",
        "financial-grafana",
        "financial-acme",
        "financial-cloudpanel-agent",
    ):
        if service not in compose_text:
            raise SystemExit(f"Compose Dockge não contém {service}")

    rendered_compose = render_dockge_compose(compose)

    with tempfile.TemporaryDirectory(prefix="argws-financial-dockge-") as tmp:
        root = Path(tmp) / "argws-financial-platform"
        root.mkdir(parents=True)
        (root / "compose.yaml").write_text(rendered_compose, encoding="utf-8")
        (root / ".env.example").write_bytes(env_example.read_bytes())
        (root / "README.md").write_bytes(readme.read_bytes())

        for folder in (*PERSISTENT_DIRS, "secrets"):
            directory = root / folder
            directory.mkdir()
            (directory / ".gitkeep").write_text("", encoding="utf-8")

        (root / "secrets" / "rclone.conf").write_text("", encoding="utf-8")
        (root / "secrets" / "backup-age-identity.txt").write_text("", encoding="utf-8")

        manifest = {
            "application": "ARGWS Financial Platform",
            "version": version,
            "deployment": "dockge-cloudpanel",
            "mode": "image-only",
            "runtime_images": "ghcr-latest",
            "published_ports": ["financial-gateway"],
            "default_domain": "finance.argws.com.br",
            "demo_domain": "demo.finance.argws.com.br",
            "tenant_wildcard": "*.finance.argws.com.br",
            "data_root": ".",
            "persistent_directories": list(PERSISTENT_DIRS),
            "internal_only_services": [
                "postgres",
                "redis",
                "rabbitmq",
                "minio",
                "prometheus",
                "grafana",
            ],
            "yaml_aliases": "expanded-none",
            "preflight_env_source": ".env",
            "automatic_domain_runtime": {
                "dns": "cloudflare-wildcard",
                "certificate": "acme-dns01",
                "cloudpanel": "host-agent-clpctl",
                "manual_step": "single-reverse-proxy",
            },
        }
        (root / "DOCKGE_PACKAGE.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(root.parent).as_posix())

    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"ZIP Dockge corrompido: {bad}")

        packaged_compose = zf.read("argws-financial-platform/compose.yaml").decode("utf-8")
        assert_alias_free_yaml(packaged_compose)
        packaged_data = yaml.safe_load(packaged_compose)
        if not isinstance(packaged_data, dict) or not isinstance(packaged_data.get("services"), dict):
            raise SystemExit("ZIP Dockge contém compose.yaml inválido")
        packaged_preflight = packaged_data["services"].get("financial-preflight") or {}
        if ".env" not in (packaged_preflight.get("env_file") or []):
            raise SystemExit("ZIP Dockge perdeu env_file .env do financial-preflight")

    print(
        json.dumps(
            {
                "status": "PASS",
                "version": version,
                "archive": str(archive),
                "sha256": sha256(archive),
                "yaml_aliases": 0,
                "services": len(packaged_data["services"]),
                "preflight_env": ".env",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
