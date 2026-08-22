#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_DIRS = (
    "data-postgres", "data-redis", "data-rabbitmq", "data-minio", "data-backups", "data-runtime",
    "data-celery", "data-prometheus", "data-grafana", "data-monitoring", "data-acme", "data-certs",
    "data-cloudpanel-agent",
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(description="Empacota a stack Dockge/CloudPanel image-only pronta para extração.")
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
        "ghcr.io/wkarts/argws-financial-api:latest", "ghcr.io/wkarts/argws-financial-web:latest",
        "ghcr.io/wkarts/argws-financial-gateway:latest", "ghcr.io/wkarts/argws-financial-acme:latest",
        "ghcr.io/wkarts/argws-financial-cloudpanel-agent:latest",
    ):
        if image not in compose_text:
            raise SystemExit(f"Compose Dockge não usa imagem esperada: {image}")
    for service in ("financial-preflight", "financial-domain-init", "financial-prometheus", "financial-grafana", "financial-acme", "financial-cloudpanel-agent"):
        if service not in compose_text:
            raise SystemExit(f"Compose Dockge não contém {service}")
    with tempfile.TemporaryDirectory(prefix="argws-financial-dockge-") as tmp:
        root = Path(tmp) / "argws-financial-platform"
        root.mkdir(parents=True)
        (root / "compose.yaml").write_bytes(compose.read_bytes())
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
            "internal_only_services": ["postgres", "redis", "rabbitmq", "minio", "prometheus", "grafana"],
            "automatic_domain_runtime": {"dns": "cloudflare-wildcard", "certificate": "acme-dns01", "cloudpanel": "host-agent-clpctl", "manual_step": "single-reverse-proxy"},
        }
        (root / "DOCKGE_PACKAGE.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(root.parent).as_posix())
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"ZIP Dockge corrompido: {bad}")
    print(json.dumps({"status": "PASS", "version": version, "archive": str(archive), "sha256": sha256(archive)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
