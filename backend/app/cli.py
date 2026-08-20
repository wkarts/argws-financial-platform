from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

import click
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.platform import PlatformSessionLocal
from app.db.tenant import tenant_engines
from app.legacy import FinancialVitorImporter
from app.models.platform import PlatformUser, Tenant
from app.models.tenant import Company, ServiceCatalog
from app.schemas.control import TenantCreate
from app.services.backup import BackupService
from app.services.provisioning import provisioning_service
from app.services.restore import RestoreService
from app.services.tenant_resolver import TenantResolver

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def run(coro):
    return asyncio.run(coro)


def migrate_platform() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic-platform.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "migrations" / "platform"))
    cfg.set_main_option("sqlalchemy.url", settings.platform_database_url_sync.replace("%", "%%"))
    command.upgrade(cfg, "head")


async def bootstrap_async() -> None:
    async with PlatformSessionLocal() as session:
        admin = await session.scalar(select(PlatformUser).where(PlatformUser.email == str(settings.platform_admin_email).lower()))
        if admin is None:
            session.add(
                PlatformUser(
                    name=settings.platform_admin_name,
                    email=str(settings.platform_admin_email).lower(),
                    password_hash=hash_password(settings.platform_admin_password),
                    role="PLATFORM_SUPERADMIN",
                    is_active=True,
                )
            )
            await session.commit()
            click.echo("Administrador do Control Plane criado.")
        else:
            click.echo("Administrador do Control Plane já existe.")
        if settings.bootstrap_demo_tenant:
            tenant = await session.scalar(select(Tenant).where(Tenant.slug == settings.demo_tenant_slug))
            if tenant is None:
                tenant, job = await provisioning_service.create_request(
                    session,
                    TenantCreate(
                        name=settings.demo_tenant_name,
                        slug=settings.demo_tenant_slug,
                        admin_name=settings.demo_tenant_admin_name,
                        admin_email=str(settings.demo_tenant_admin_email),
                        admin_password=settings.demo_tenant_admin_password,
                        initial_company_name=settings.demo_tenant_name,
                        initial_company_tax_id="00000000000191",
                    ),
                    actor_id=None,
                )
                await provisioning_service.provision(str(job.id))
                click.echo(f"Tenant demo provisionado: {settings.tenant_hostname(tenant.slug)}")
            else:
                click.echo("Tenant demo já existe.")


@click.group()
def cli() -> None:
    """Administração da ARGWS Financial Platform."""


@cli.command("migrate-platform")
def migrate_platform_command() -> None:
    migrate_platform()
    click.echo("Migrations do Control Plane aplicadas.")


@cli.command("bootstrap")
def bootstrap_command() -> None:
    run(bootstrap_async())


@cli.command("init")
def init_command() -> None:
    migrate_platform()
    run(bootstrap_async())
    click.echo("Inicialização concluída.")


@cli.command("backup")
def backup_command() -> None:
    async def action() -> None:
        async with PlatformSessionLocal() as session:
            result = await BackupService(session).create_full()
            click.echo(json.dumps({"id": str(result.id), "path": result.path, "sha256": result.checksum}, indent=2))
    run(action())


@cli.command("restore")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
@click.option("--identity", type=click.Path(exists=True, path_type=Path), default=None, help="Chave privada age para backup criptografado.")
@click.option("--sha256", "expected_sha256", default=None, help="SHA-256 esperado do arquivo externo.")
@click.option("--yes", is_flag=True, help="Confirma a restauração destrutiva.")
def restore_command(archive: Path, identity: Path | None, expected_sha256: str | None, yes: bool) -> None:
    if not yes:
        raise click.ClickException("Restauração não confirmada. Use --yes após parar API, workers e beat.")

    async def action() -> None:
        result = await RestoreService().restore_full(archive, identity=identity, expected_sha256=expected_sha256)
        click.echo(json.dumps({
            "archive": result.archive,
            "platform_database": result.platform_database,
            "tenants_restored": result.tenants_restored,
            "buckets_restored": result.buckets_restored,
            "manifest_version": result.manifest_version,
        }, ensure_ascii=False, indent=2))

    run(action())


@cli.command("legacy-preview")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
@click.option("--output", type=click.Path(path_type=Path), default=None)
def legacy_preview(archive: Path, output: Path | None) -> None:
    report = FinancialVitorImporter().preview(archive).to_dict()
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if output:
        output.write_text(content, encoding="utf-8")
        click.echo(str(output))
    else:
        click.echo(content)


@cli.command("legacy-import")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
@click.option("--tenant-id", required=True)
@click.option("--company-id", required=True)
@click.option("--service-id", required=True)
def legacy_import(archive: Path, tenant_id: str, company_id: str, service_id: str) -> None:
    async def action() -> None:
        async with PlatformSessionLocal() as platform_session:
            context = await TenantResolver(platform_session).resolve_by_id(tenant_id)
            entry = await tenant_engines.get(context)
            async with entry.session_factory() as session:
                stats = await FinancialVitorImporter().import_into(
                    session,
                    archive,
                    company_id=company_id,
                    service_id=service_id,
                )
                click.echo(json.dumps(stats, ensure_ascii=False, indent=2))
    run(action())


if __name__ == "__main__":
    cli()
