from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import unicodedata


def ascii_text(value: str, length: int, align: str = "left", fill: str = " ") -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    normalized = " ".join(normalized.upper().split())[:length]
    return normalized.rjust(length, fill) if align == "right" else normalized.ljust(length, fill)


def numeric(value: str | int | Decimal, length: int) -> str:
    if isinstance(value, Decimal):
        raw = str(int(value * 100))
    else:
        raw = "".join(ch for ch in str(value) if ch.isdigit())
    return raw[-length:].rjust(length, "0")


def ddmmyyyy(value: date) -> str:
    return value.strftime("%d%m%Y")


def record(*parts: str) -> str:
    value = "".join(parts)
    if len(value) > 240:
        raise ValueError(f"Registro CNAB maior que 240 posições: {len(value)}")
    return value.ljust(240)


@dataclass(frozen=True, slots=True)
class CNABTitle:
    document_number: str
    our_number: str
    due_date: date
    amount: Decimal
    payer_name: str
    payer_tax_id: str
    payer_address: str = ""
    payer_zip_code: str = ""
    payer_city: str = ""
    payer_state: str = ""


@dataclass(frozen=True, slots=True)
class CNABCompany:
    bank_code: str
    tax_id: str
    name: str
    agreement: str
    branch: str
    branch_digit: str
    account: str
    account_digit: str


class CNAB240Generator:
    """Núcleo CNAB 240 extensível.

    Os registros respeitam 240 posições e a estrutura FEBRABAN de arquivo/lote,
    mas cada banco exige homologação de campos, códigos de ocorrência e carteira.
    Adapters bancários devem especializar os métodos de segmento.
    """

    def __init__(self, company: CNABCompany, sequence: int, generation_date: date) -> None:
        self.company = company
        self.sequence = sequence
        self.generation_date = generation_date

    def file_header(self) -> str:
        c = self.company
        return record(
            numeric(c.bank_code, 3), "0000", "0", " " * 9, "2", numeric(c.tax_id, 14),
            ascii_text(c.agreement, 20), numeric(c.branch, 5), ascii_text(c.branch_digit, 1),
            numeric(c.account, 12), ascii_text(c.account_digit, 1), " ", ascii_text(c.name, 30),
            ascii_text("BANCO", 30), " " * 10, "1", ddmmyyyy(self.generation_date), "000000",
            numeric(self.sequence, 6), "103", "00000", " " * 20,
        )

    def lot_header(self) -> str:
        c = self.company
        return record(
            numeric(c.bank_code, 3), "0001", "1", "R", "01", "00", "030", " ", "2",
            numeric(c.tax_id, 15), ascii_text(c.agreement, 20), numeric(c.branch, 5),
            ascii_text(c.branch_digit, 1), numeric(c.account, 12), ascii_text(c.account_digit, 1),
            " ", ascii_text(c.name, 30), " " * 40, ascii_text("COBRANCA", 40),
        )

    def segment_p(self, title: CNABTitle, sequence: int) -> str:
        c = self.company
        return record(
            numeric(c.bank_code, 3), "0001", "3", numeric(sequence, 5), "P", " ", "01",
            numeric(c.branch, 5), ascii_text(c.branch_digit, 1), numeric(c.account, 12),
            ascii_text(c.account_digit, 1), " ", ascii_text(title.our_number, 20), "1", "1", "1", "2", "2",
            ascii_text(title.document_number, 15), ddmmyyyy(title.due_date), numeric(title.amount, 15),
            "00000", " ", "01", ddmmyyyy(self.generation_date), "0", "00000000", numeric(0, 15),
            "0", "00000000", numeric(0, 15), numeric(0, 15), ascii_text(title.document_number, 25),
            "3", "00000000", "000000000000000", " " * 11,
        )

    def segment_q(self, title: CNABTitle, sequence: int) -> str:
        payer_type = "1" if len("".join(ch for ch in title.payer_tax_id if ch.isdigit())) <= 11 else "2"
        return record(
            numeric(self.company.bank_code, 3), "0001", "3", numeric(sequence, 5), "Q", " ", "01",
            payer_type, numeric(title.payer_tax_id, 15), ascii_text(title.payer_name, 40),
            ascii_text(title.payer_address, 40), "00000", "000", numeric(title.payer_zip_code, 8),
            ascii_text(title.payer_city, 15), ascii_text(title.payer_state, 2), "0", "0" * 15,
            ascii_text("", 40), "000", " " * 20,
        )

    def lot_trailer(self, title_count: int, total: Decimal) -> str:
        record_count = 2 + title_count * 2 + 1
        return record(
            numeric(self.company.bank_code, 3), "0001", "5", " " * 9,
            numeric(record_count, 6), numeric(title_count, 6), numeric(total, 17), "0" * 6, "0" * 17,
            "0" * 6, "0" * 17, "0" * 6, "0" * 17, " " * 8, " " * 117,
        )

    def file_trailer(self, record_count: int) -> str:
        return record(
            numeric(self.company.bank_code, 3), "9999", "9", " " * 9, "000001",
            numeric(record_count, 6), "000000", " " * 205,
        )

    def generate(self, titles: list[CNABTitle]) -> bytes:
        lines = [self.file_header(), self.lot_header()]
        seq = 1
        for title in titles:
            lines.append(self.segment_p(title, seq)); seq += 1
            lines.append(self.segment_q(title, seq)); seq += 1
        total = sum((item.amount for item in titles), Decimal("0"))
        lines.append(self.lot_trailer(len(titles), total))
        lines.append(self.file_trailer(len(lines) + 1))
        if any(len(line) != 240 for line in lines):
            raise ValueError("CNAB inválido: todos os registros devem ter 240 posições.")
        return ("\r\n".join(lines) + "\r\n").encode("ascii")


class CNAB240ReturnParser:
    def parse(self, content: bytes) -> list[dict[str, str]]:
        text = content.decode("latin-1")
        lines = [line.rstrip("\r\n") for line in text.splitlines() if line.strip()]
        if any(len(line) != 240 for line in lines):
            raise ValueError("Arquivo de retorno CNAB 240 possui registro com tamanho inválido.")
        events: list[dict[str, str]] = []
        for line in lines:
            if line[7:8] != "3":
                continue
            segment = line[13:14]
            if segment not in {"T", "U"}:
                continue
            events.append(
                {
                    "segment": segment,
                    "sequence": line[8:13],
                    "occurrence_code": line[15:17],
                    "our_number": line[37:57].strip(),
                    "document_number": line[58:73].strip(),
                    "raw": line,
                }
            )
        return events
