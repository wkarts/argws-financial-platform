from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import APIError
from app.models.tenant import BankAgreement, Charge, Customer, OutboxEvent, Payment, Receivable
from app.providers.banking import BankChargeRequest, BankCustomer, banking_providers


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_charge(
        self,
        *,
        receivable_id: str,
        provider_name: str = "SANDBOX",
        charge_type: str = "BOLETO_PIX",
        bank_agreement_id: str | None = None,
    ) -> Charge:
        receivable = await self.session.scalar(
            select(Receivable).where(Receivable.id == receivable_id).with_for_update()
        )
        if receivable is None:
            raise APIError("RECEIVABLE_NOT_FOUND", "Conta a receber não encontrada.", 404)
        if receivable.status in {"PAID", "CANCELLED", "REVERSED"}:
            raise APIError("RECEIVABLE_NOT_CHARGEABLE", "Este recebível não pode ser cobrado.", 409)
        customer = await self.session.get(Customer, receivable.customer_id)
        if customer is None:
            raise APIError("CUSTOMER_NOT_FOUND", "Cliente não encontrado.", 404)

        agreement_data: dict[str, object] = {}
        if bank_agreement_id:
            agreement = await self.session.get(BankAgreement, bank_agreement_id)
            if agreement is None or not agreement.is_active:
                raise APIError("BANK_AGREEMENT_NOT_FOUND", "Convênio bancário não encontrado ou inativo.", 404)
            if agreement.company_id != receivable.company_id:
                raise APIError(
                    "BANK_AGREEMENT_COMPANY_MISMATCH",
                    "O convênio bancário não pertence à empresa emissora do recebível.",
                    409,
                )
            provider_name = agreement.provider
            agreement_data = {
                "id": str(agreement.id),
                "number": agreement.agreement_number,
                "wallet": agreement.wallet,
                "beneficiary_code": agreement.beneficiary_code,
                "settings": agreement.settings,
            }

        active_charge = await self.session.scalar(
            select(Charge)
            .where(
                Charge.receivable_id == receivable.id,
                Charge.status.notin_(["CANCELLED", "REVERSED", "FAILED", "EXPIRED"]),
            )
            .order_by(Charge.created_at.desc())
        )
        if active_charge is not None:
            return active_charge

        provider = banking_providers.get(provider_name)
        result = await provider.create_charge(
            BankChargeRequest(
                internal_id=str(receivable.id),
                document_number=receivable.document_number,
                amount=Decimal(receivable.balance),
                due_date=receivable.due_date,
                description=receivable.description,
                customer=BankCustomer(
                    name=customer.name,
                    tax_id=customer.tax_id,
                    email=customer.email,
                    phone=customer.phone,
                    address=customer.address,
                ),
                charge_type=charge_type,
                agreement=agreement_data,
            )
        )
        existing = await self.session.scalar(
            select(Charge).where(Charge.provider == result.provider, Charge.external_id == result.external_id)
        )
        if existing is not None:
            if existing.receivable_id != receivable.id:
                raise APIError(
                    "BANK_EXTERNAL_ID_COLLISION",
                    "O identificador externo retornado pelo banco já pertence a outro recebível.",
                    409,
                )
            receivable.status = "REGISTERED"
            await self.session.commit()
            return existing
        charge = Charge(
            receivable_id=receivable.id,
            bank_agreement_id=bank_agreement_id,
            charge_type=charge_type,
            provider=result.provider,
            external_id=result.external_id,
            our_number=result.our_number,
            txid=result.txid,
            digitable_line=result.digitable_line,
            barcode=result.barcode,
            pix_copy_paste=result.pix_copy_paste,
            document_url=result.document_url,
            status=result.status,
            registered_at=datetime.now(UTC),
            raw_response=result.raw,
        )
        self.session.add(charge)
        receivable.status = "REGISTERED"
        await self.session.flush()
        self.session.add(
            OutboxEvent(
                aggregate_type="Charge",
                aggregate_id=str(charge.id),
                event_type="financial.charge.registered",
                payload={
                    "charge_id": str(charge.id),
                    "receivable_id": str(receivable.id),
                    "customer_id": str(customer.id),
                    "company_id": str(receivable.company_id),
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(charge)
        return charge

    async def register_payment(
        self,
        *,
        receivable_id: str,
        provider: str,
        external_id: str,
        amount: Decimal,
        paid_at: datetime,
        payment_method: str,
        charge_id: str | None = None,
        end_to_end_id: str | None = None,
        raw_payload: dict[str, object] | None = None,
    ) -> Payment:
        existing = await self.session.scalar(
            select(Payment).where(Payment.provider == provider, Payment.external_id == external_id)
        )
        if existing is not None:
            return existing
        receivable = await self.session.scalar(
            select(Receivable).where(Receivable.id == receivable_id).with_for_update()
        )
        if receivable is None:
            raise APIError("RECEIVABLE_NOT_FOUND", "Conta a receber não encontrada.", 404)
        # Outro worker pode ter concluído o mesmo evento enquanto aguardávamos o lock.
        existing = await self.session.scalar(
            select(Payment).where(Payment.provider == provider, Payment.external_id == external_id)
        )
        if existing is not None:
            return existing
        if charge_id:
            charge = await self.session.get(Charge, charge_id)
            if charge is None or charge.receivable_id != receivable.id:
                raise APIError(
                    "PAYMENT_CHARGE_MISMATCH",
                    "A cobrança informada não pertence ao recebível.",
                    409,
                )
        if amount <= 0:
            raise APIError("INVALID_PAYMENT_AMOUNT", "O pagamento precisa ser maior que zero.", 422)
        if paid_at.tzinfo is None:
            paid_at = paid_at.replace(tzinfo=UTC)
        payment = Payment(
            receivable_id=receivable.id,
            charge_id=charge_id,
            provider=provider,
            external_id=external_id,
            end_to_end_id=end_to_end_id,
            amount=amount,
            paid_at=paid_at,
            payment_method=payment_method,
            status="CONFIRMED",
            raw_payload=raw_payload or {},
        )
        self.session.add(payment)
        receivable.paid_amount = Decimal(receivable.paid_amount) + amount
        receivable.balance = max(Decimal(receivable.balance) - amount, Decimal("0"))
        receivable.status = "PAID" if receivable.balance == 0 else "PARTIALLY_PAID"
        await self.session.flush()
        self.session.add(
            OutboxEvent(
                aggregate_type="Payment",
                aggregate_id=str(payment.id),
                event_type="financial.payment.confirmed",
                payload={
                    "payment_id": str(payment.id),
                    "receivable_id": str(receivable.id),
                    "company_id": str(receivable.company_id),
                    "customer_id": str(receivable.customer_id),
                    "amount": str(amount),
                    "receivable_status": receivable.status,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(payment)
        return payment
