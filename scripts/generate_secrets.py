#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import re
import secrets
import stat
from pathlib import Path



def token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def load_env(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def parse(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def replace(lines: list[str], values: dict[str, str]) -> list[str]:
    output: list[str] = []
    found: set[str] = set()
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in values:
            output.append(f"{key}={values[key]}")
            found.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in found:
            output.append(f"{key}={value}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera segredos consistentes para a stack ARGWS Financial Platform.")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--force", action="store_true", help="Regenera inclusive valores já preenchidos.")
    args = parser.parse_args()
    if not args.env.exists():
        raise SystemExit(f"Arquivo não encontrado: {args.env}")
    lines = load_env(args.env)
    current = parse(lines)

    generated = {
        "APP_SECRET_KEY": token(64),
        "FIELD_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "POSTGRES_PASSWORD": token(36),
        "RABBITMQ_PASSWORD": token(36),
        "MINIO_ROOT_PASSWORD": token(36),
        "PLATFORM_ADMIN_PASSWORD": token(24),
        "DEMO_TENANT_ADMIN_PASSWORD": token(24),
        "DOMAIN_RECONCILIATION_TOKEN": token(48),
        "EVOLUTION_WEBHOOK_SECRET": token(48),
        "BANKING_WEBHOOK_SECRET": token(48),
    }
    values: dict[str, str] = {}
    for key, value in generated.items():
        existing = current.get(key, "")
        if args.force or not existing or existing.startswith("CHANGE_ME"):
            values[key] = value
        else:
            values[key] = existing

    values["POSTGRES_ADMIN_PASSWORD"] = values["POSTGRES_PASSWORD"]
    # A stack padrão usa o MinIO interno; as credenciais S3 precisam ser exatamente
    # as credenciais root configuradas no container MinIO. Para S3 externo, ajuste
    # S3_ACCESS_KEY/S3_SECRET_KEY manualmente depois da geração inicial.
    values["S3_ACCESS_KEY"] = current.get("MINIO_ROOT_USER") or "financial"
    values["S3_SECRET_KEY"] = values["MINIO_ROOT_PASSWORD"]
    values["RABBITMQ_URL"] = f"amqp://{current.get('RABBITMQ_USER','financial')}:{values['RABBITMQ_PASSWORD']}@financial-rabbitmq:5672/financial"
    values["CELERY_BROKER_URL"] = values["RABBITMQ_URL"]

    args.env.write_text("\n".join(replace(lines, values)) + "\n", encoding="utf-8")
    args.env.chmod(stat.S_IRUSR | stat.S_IWUSR)

    credentials = args.env.parent / ".bootstrap-credentials.txt"
    credentials.write_text(
        "\n".join([
            "ARGWS Financial Platform — credenciais iniciais",
            f"Control Plane: {current.get('PUBLIC_SCHEME','https')}://{current.get('CONTROL_PLANE_HOST','control.localhost')}",
            f"Usuário: {current.get('PLATFORM_ADMIN_EMAIL','admin@example.com')}",
            f"Senha: {values['PLATFORM_ADMIN_PASSWORD']}",
            "",
            f"Tenant demo: {current.get('PUBLIC_SCHEME','https')}://{current.get('DEMO_TENANT_SLUG','demo')}.{current.get('TENANT_DOMAIN_ROOT','localhost')}",
            f"Usuário demo: {current.get('DEMO_TENANT_ADMIN_EMAIL','admin.demo@example.com')}",
            f"Senha demo: {values['DEMO_TENANT_ADMIN_PASSWORD']}",
            "",
            "Troque as senhas após o primeiro acesso e guarde este arquivo fora do servidor.",
        ]) + "\n",
        encoding="utf-8",
    )
    credentials.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Segredos gravados em {args.env}")
    print(f"Credenciais iniciais gravadas em {credentials}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
