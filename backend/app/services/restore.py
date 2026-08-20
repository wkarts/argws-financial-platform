from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.secrets import secret_cipher
from app.db.platform import PlatformSessionLocal, platform_engine
from app.db.postgres_admin import connect_postgres_admin
from app.models.platform import Tenant, TenantDatabase, TenantStorage
from app.services.backup import BackupError, run_command, safe_backup_path, sha256_file
from app.services.provisioning import sql_identifier, sql_literal


@dataclass(frozen=True, slots=True)
class RestoreResult:
    archive: str
    platform_database: str
    tenants_restored: int
    buckets_restored: int
    manifest_version: int


class RestoreService:
    """Restauração integral e verificável da plataforma.

    Deve ser executada com API, workers e scheduler parados. O comando cria um
    maintenance flag para bloquear acessos acidentais ao gateway durante o
    procedimento e o remove apenas após validação bem-sucedida.
    """

    async def _extract(self, archive: Path, destination: Path, identity: Path | None) -> Path:
        source = archive
        if archive.suffix == ".age":
            key = identity or settings.backup_encryption_identity
            if not key.exists():
                raise BackupError(f"Identidade age não encontrada: {key}")
            source = destination / "decrypted.tar.zst"
            await run_command(["age", "-d", "-i", str(key), "-o", str(source), str(archive)])

        members = await run_command(["tar", "--zstd", "-tf", str(source)])
        for member in members.splitlines():
            if member.strip():
                safe_backup_path(destination, member)
        verbose = await run_command(["tar", "--zstd", "-tvf", str(source)])
        for line in verbose.splitlines():
            if line and line[0] not in {"-", "d"}:
                raise BackupError("Backup contém link ou tipo de entrada não permitido.")

        await run_command([
            "tar", "--zstd", "--no-same-owner", "--no-same-permissions",
            "-xf", str(source), "-C", str(destination),
        ])
        return destination

    @staticmethod
    def _verify_checksums(root: Path) -> None:
        checksum_file = root / "checksums.sha256"
        if not checksum_file.exists():
            raise BackupError("Arquivo checksums.sha256 ausente no backup.")
        for line in checksum_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                expected, relative = line.split("  ", 1)
            except ValueError as exc:
                raise BackupError("Linha inválida em checksums.sha256.") from exc
            if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected.lower()):
                raise BackupError(f"SHA-256 inválido no manifesto: {expected!r}")
            path = safe_backup_path(root, relative)
            if not path.is_file():
                raise BackupError(f"Arquivo referenciado no checksum não existe: {relative}")
            actual = sha256_file(path)
            if actual != expected:
                raise BackupError(f"Checksum inválido para {relative}: esperado {expected}, obtido {actual}")

    async def _restore_database(self, dump: Path, database: str, user: str, password: str) -> None:
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        await run_command(
            [
                "pg_restore",
                "--host", settings.postgres_host,
                "--port", str(settings.postgres_port),
                "--username", user,
                "--dbname", database,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                str(dump),
            ],
            env=env,
        )

    async def _terminate_connections(self, database: str) -> None:
        conn = await connect_postgres_admin()
        try:
            await conn.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname=$1 and pid <> pg_backend_pid()",
                database,
            )
        finally:
            await conn.close()

    async def _ensure_tenant_database(self, record: TenantDatabase) -> str:
        password = secret_cipher.decrypt(record.encrypted_password)
        conn = await connect_postgres_admin()
        try:
            role_exists = await conn.fetchval("select 1 from pg_roles where rolname=$1", record.database_user)
            if role_exists:
                await conn.execute(
                    f"alter role {sql_identifier(record.database_user)} password {sql_literal(password)}"
                )
            else:
                await conn.execute(
                    f"create role {sql_identifier(record.database_user)} login password {sql_literal(password)} "
                    "nosuperuser nocreatedb nocreaterole inherit"
                )
            db_exists = await conn.fetchval("select 1 from pg_database where datname=$1", record.database_name)
            if not db_exists:
                await conn.execute(
                    f"create database {sql_identifier(record.database_name)} owner {sql_identifier(record.database_user)} "
                    "encoding 'UTF8' template template0"
                )
            else:
                await conn.execute(
                    f"alter database {sql_identifier(record.database_name)} owner to {sql_identifier(record.database_user)}"
                )
        finally:
            await conn.close()
        return password

    async def _restore_bucket(self, root: Path, bucket: str) -> None:
        source = root / "objects" / bucket
        if not source.exists():
            return
        env = {
            **os.environ,
            "RCLONE_S3_PROVIDER": "Minio",
            "RCLONE_S3_ENDPOINT": settings.s3_endpoint_url,
            "RCLONE_S3_ACCESS_KEY_ID": settings.s3_access_key,
            "RCLONE_S3_SECRET_ACCESS_KEY": settings.s3_secret_key,
        }
        await run_command(
            [
                "rclone", "copy", str(source), f":s3:{bucket}",
                "--fast-list", "--checksum", "--create-empty-src-dirs",
            ],
            env=env,
        )

    async def restore_full(
        self,
        archive: Path,
        *,
        identity: Path | None = None,
        expected_sha256: str | None = None,
    ) -> RestoreResult:
        archive = archive.resolve()
        if not archive.is_file():
            raise BackupError(f"Backup não encontrado: {archive}")
        if expected_sha256 and sha256_file(archive) != expected_sha256.lower():
            raise BackupError("SHA-256 do arquivo de backup não corresponde ao valor informado.")
        settings.maintenance_file.parent.mkdir(parents=True, exist_ok=True)
        settings.maintenance_file.write_text(
            json.dumps({"reason": "restore", "archive": str(archive)}, ensure_ascii=False),
            encoding="utf-8",
        )
        temp = Path(tempfile.mkdtemp(prefix="restore-", dir=settings.backup_dir))
        succeeded = False
        try:
            root = await self._extract(archive, temp, identity)
            self._verify_checksums(root)
            manifest_path = root / "manifest.json"
            if not manifest_path.exists():
                raise BackupError("manifest.json ausente no backup.")
            manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("scope") != "FULL":
                raise BackupError("O arquivo informado não é um backup FULL.")
            if int(manifest.get("format", 0)) != 1:
                raise BackupError(f"Versão de backup não suportada: {manifest.get('format')!r}")

            await platform_engine.dispose()
            await self._terminate_connections(settings.postgres_db)
            platform_dump = safe_backup_path(
                root, f"databases/{manifest['platform_database']['file']}"
            )
            if not platform_dump.is_file():
                raise BackupError("Dump do Control Plane ausente no backup.")
            await self._restore_database(
                platform_dump,
                settings.postgres_db,
                settings.postgres_user,
                settings.postgres_password,
            )

            tenant_manifest = {str(item["tenant_id"]): item for item in manifest.get("tenants", [])}
            try:
                tenant_ids = [UUID(value) for value in tenant_manifest]
            except (TypeError, ValueError) as exc:
                raise BackupError("Manifest contém tenant_id inválido.") from exc
            tenants_restored = 0
            buckets_restored = 0
            async with PlatformSessionLocal() as session:
                tenants = list((await session.execute(
                    select(Tenant)
                    .options(selectinload(Tenant.database), selectinload(Tenant.storage))
                    .where(Tenant.id.in_(tenant_ids))
                )).scalars())
                found_ids = {str(tenant.id) for tenant in tenants}
                missing_ids = sorted(set(tenant_manifest) - found_ids)
                if missing_ids:
                    raise BackupError(
                        "Tenants do manifesto ausentes após restaurar o Control Plane: "
                        + ", ".join(missing_ids)
                    )
                for tenant in tenants:
                    entry = tenant_manifest.get(str(tenant.id))
                    if not entry or tenant.database is None:
                        continue
                    password = await self._ensure_tenant_database(tenant.database)
                    await self._terminate_connections(tenant.database.database_name)
                    dump = safe_backup_path(root, f"databases/{entry['database']['file']}")
                    if not dump.is_file():
                        raise BackupError(f"Dump ausente para o tenant {tenant.slug}.")
                    await self._restore_database(
                        dump,
                        tenant.database.database_name,
                        tenant.database.database_user,
                        password,
                    )
                    tenants_restored += 1
                    storage_info = entry.get("storage")
                    if storage_info and tenant.storage:
                        await self._restore_bucket(root, tenant.storage.bucket)
                        buckets_restored += 1

            succeeded = True
            return RestoreResult(
                archive=str(archive),
                platform_database=settings.postgres_db,
                tenants_restored=tenants_restored,
                buckets_restored=buckets_restored,
                manifest_version=int(manifest.get("format", 1)),
            )
        finally:
            shutil.rmtree(temp, ignore_errors=True)
            if succeeded:
                settings.maintenance_file.unlink(missing_ok=True)
