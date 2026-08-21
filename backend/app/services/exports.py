from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.tenant import Charge, Customer, ExportJob, Payment, Receivable
from app.providers.storage import S3StorageProvider


class ExportService:
    def __init__(self, session: AsyncSession, *, bucket: str) -> None:
        self.session = session
        self.bucket = bucket
        self.storage = S3StorageProvider()

    @staticmethod
    def _value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    async def _dataset(self, export_type: str, filters: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
        export_type = export_type.upper()
        if export_type == "RECEIVABLES":
            stmt = select(Receivable).order_by(Receivable.due_date)
            if filters.get("status"):
                stmt = stmt.where(Receivable.status == str(filters["status"]).upper())
            if filters.get("company_id"):
                stmt = stmt.where(Receivable.company_id == UUID(str(filters["company_id"])))
            items = list((await self.session.scalars(stmt.limit(100000))).all())
            headers = ["id", "company_id", "customer_id", "document_number", "competence", "description", "issue_date", "due_date", "original_amount", "paid_amount", "balance", "status", "source"]
            rows = [[getattr(item, name) for name in headers] for item in items]
            return headers, rows
        if export_type == "CUSTOMERS":
            items = list((await self.session.scalars(select(Customer).order_by(Customer.name).limit(100000))).all())
            headers = ["id", "person_type", "name", "trade_name", "tax_id", "email", "phone", "whatsapp", "is_active", "created_at"]
            return headers, [[getattr(item, name) for name in headers] for item in items]
        if export_type == "PAYMENTS":
            items = list((await self.session.scalars(select(Payment).order_by(Payment.paid_at.desc()).limit(100000))).all())
            headers = ["id", "receivable_id", "charge_id", "provider", "external_id", "end_to_end_id", "amount", "paid_at", "payment_method", "status"]
            return headers, [[getattr(item, name) for name in headers] for item in items]
        if export_type == "CHARGES":
            items = list((await self.session.scalars(select(Charge).order_by(Charge.created_at.desc()).limit(100000))).all())
            headers = ["id", "receivable_id", "bank_agreement_id", "charge_type", "provider", "external_id", "our_number", "txid", "status", "registered_at", "created_at"]
            return headers, [[getattr(item, name) for name in headers] for item in items]
        raise APIError("EXPORT_TYPE_UNSUPPORTED", "Tipo de exportação não suportado.", 422, {"export_type": export_type})

    async def create(self, *, export_type: str, format_name: str, filters: dict[str, Any], requested_by: UUID | None) -> ExportJob:
        item = ExportJob(export_type=export_type.upper(), status="PROCESSING", filters=filters, format=format_name.upper(), requested_by=requested_by)
        self.session.add(item)
        await self.session.flush()
        try:
            headers, rows = await self._dataset(item.export_type, filters)
            output = io.BytesIO()
            if item.format == "CSV":
                text = io.StringIO()
                writer = csv.writer(text, delimiter=";", lineterminator="\n")
                writer.writerow(headers)
                for row in rows:
                    writer.writerow([self._value(value) for value in row])
                content = text.getvalue().encode("utf-8-sig")
                extension, mime = "csv", "text/csv"
            elif item.format == "XLSX":
                workbook = Workbook(write_only=True)
                sheet = workbook.create_sheet(title=item.export_type[:31])
                sheet.append(headers)
                for row in rows:
                    sheet.append([self._value(value) for value in row])
                workbook.save(output)
                content = output.getvalue()
                extension = "xlsx"
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                raise APIError("EXPORT_FORMAT_UNSUPPORTED", "Formato de exportação não suportado.", 422, {"format": item.format})
            filename = f"{item.export_type.lower()}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.{extension}"
            key = f"exports/{item.id}/{filename}"
            stored = await self.storage.put_bytes(self.bucket, key, content, mime)
            item.object_key = stored.key
            item.sha256 = stored.sha256
            item.size_bytes = stored.size
            item.status = "COMPLETED"
            item.finished_at = datetime.now(UTC)
        except Exception as exc:
            item.status = "FAILED"
            item.last_error = str(exc)[:4000]
            item.finished_at = datetime.now(UTC)
            await self.session.commit()
            raise
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def signed_url(self, item: ExportJob) -> str | None:
        if not item.object_key:
            return None
        return await self.storage.presigned_url(self.bucket, item.object_key, expires=900)
