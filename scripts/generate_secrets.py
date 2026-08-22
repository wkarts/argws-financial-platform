#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import secrets
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def canonical_version() -> str:
    version_file = ROOT / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit(f"VERSION vazia: {version_file}")
    return version


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
    parser = argparse.ArgumentParser(description="Gera/repara segredos consistentes para ARGWS Financial Platform.")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenera inclusive credenciais primárias já preenchidas. Não use em stack com dados sem planejar a rotação.",
    )
    args = parser.parse_args()
    if not args.env.exists():
        raise SystemExit(f"Arquivo não encontrado: {args.env}")

    lines = load_env(args.env)
    current = parse(lines)
    version = canonical_version()

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
        "GRAFANA_ADMIN_PASSWORD": token(24),
        "CLOUDPANEL_SITE_USER_PASSWORD": token(24),
    }
    values: dict[str, str] = {}
    for key, value in generated.items():
        existing = current.get(key, "")
        if args.force or not existing or existing.startswith("CHANGE_ME") or existing.startswith("__CONFIGURE_"):
            values[key] = value
        else:
            values[key] = existing

    # VERSION continua sendo a única fonte canônica. Esses campos são apenas
    # espelhos gerados para ferramentas legadas; os containers publicados leem
    # a VERSION embutida na imagem.
    values["APP_VERSION"] = version
    values["VITE_APP_VERSION"] = version

    # O container oficial do Postgres cria apenas POSTGRES_USER. Se o usuário
    # administrativo for o mesmo, a senha necessariamente é a mesma.
    admin_user = current.get("POSTGRES_ADMIN_USER") or current.get("POSTGRES_USER") or "financial_admin"
    postgres_user = current.get("POSTGRES_USER") or "financial_admin"
    if admin_user == postgres_user:
        values["POSTGRES_ADMIN_PASSWORD"] = values["POSTGRES_PASSWORD"]
    else:
        existing_admin_password = current.get("POSTGRES_ADMIN_PASSWORD", "")
        values["POSTGRES_ADMIN_PASSWORD"] = (
            token(36)
            if args.force or not existing_admin_password or existing_admin_password.startswith("CHANGE_ME")
            else existing_admin_password
        )

    # A stack padrão usa MinIO interno. Quando S3_ACCESS_KEY aponta para o root
    # do MinIO, o segredo S3 deve acompanhar exatamente a credencial do MinIO.
    minio_user = current.get("MINIO_ROOT_USER") or "financial"
    values["S3_ACCESS_KEY"] = minio_user
    values["S3_SECRET_KEY"] = values["MINIO_ROOT_PASSWORD"]

    rabbit_user = current.get("RABBITMQ_USER") or "financial"
    values["RABBITMQ_URL"] = (
        f"amqp://{rabbit_user}:{values['RABBITMQ_PASSWORD']}@financial-rabbitmq:5672/financial"
    )
    values["CELERY_BROKER_URL"] = values["RABBITMQ_URL"]

    # Corrige a grafia inválida que já apareceu em instalações e alinha porta
    # SMTPS 465 com o modo ssl. O SMTP pode continuar desabilitado.
    smtp_security = current.get("SMTP_SECURITY", "starttls").strip().lower()
    smtp_port = current.get("SMTP_PORT", "587").strip()
    if smtp_security == "startssl":
        smtp_security = "ssl" if smtp_port == "465" else "starttls"
    if smtp_port == "465" and smtp_security == "starttls":
        smtp_security = "ssl"
    if smtp_security not in {"none", "starttls", "ssl"}:
        smtp_security = "starttls"
    values["SMTP_SECURITY"] = smtp_security

    final_lines = replace(lines, values)
    args.env.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
    args.env.chmod(stat.S_IRUSR | stat.S_IWUSR)

    final_values = parse(final_lines)
    credentials = args.env.parent / ".bootstrap-credentials.txt"
    credential_lines = [
        f"ARGWS Financial Platform {version} — credenciais iniciais",
        f"Control Plane: {final_values.get('PUBLIC_SCHEME','https')}://{final_values.get('CONTROL_PLANE_HOST','control.localhost')}",
        f"Usuário: {final_values.get('PLATFORM_ADMIN_EMAIL','admin@example.com')}",
        f"Senha: {values['PLATFORM_ADMIN_PASSWORD']}",
    ]
    if final_values.get("BOOTSTRAP_DEMO_TENANT", "false").lower() == "true":
        credential_lines.extend([
            "",
            f"Tenant demo: {final_values.get('PUBLIC_SCHEME','https')}://{final_values.get('DEMO_TENANT_SLUG','demo')}.{final_values.get('TENANT_DOMAIN_ROOT','localhost')}",
            f"Usuário demo: {final_values.get('DEMO_TENANT_ADMIN_EMAIL','admin.demo@example.com')}",
            f"Senha demo: {values['DEMO_TENANT_ADMIN_PASSWORD']}",
        ])
    credential_lines.extend([
        "",
        "Troque as senhas após o primeiro acesso e guarde este arquivo fora do servidor.",
    ])
    credentials.write_text("\n".join(credential_lines) + "\n", encoding="utf-8")
    credentials.chmod(stat.S_IRUSR | stat.S_IWUSR)

    print(f"Versão sincronizada: {version}")
    print(f"Segredos e dependências reparados em {args.env}")
    print(f"Credenciais iniciais gravadas em {credentials}")
    print("Execute o preflight antes do deploy: docker compose run --rm financial-preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
