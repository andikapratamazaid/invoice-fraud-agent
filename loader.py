"""Loader dataset Invoice Fraud & Three-Way Match Agent.

Membaca empat berkas data dari folder samples:
- vendors.json   : master vendor (termasuk nomor rekening bank)
- pos.csv        : purchase order, satu baris per item
- receipts.csv   : berita acara penerimaan barang (BAST), satu baris per item
- invoices.csv   : invoice vendor, satu baris per item

Semua nominal uang berupa integer rupiah.
"""

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


def _parse_date(text):
    text = (text or "").strip()
    if not text:
        return None
    return date.fromisoformat(text)


@dataclass
class Vendor:
    vendor_id: str
    name: str
    bank_name: str
    bank_account: str
    city: str = ""


@dataclass
class POLine:
    line_no: int
    item_name: str
    unit: str
    qty: int
    unit_price: int

    @property
    def amount(self):
        return self.qty * self.unit_price


@dataclass
class PO:
    po_id: str
    vendor_id: str
    po_date: date
    lines: list = field(default_factory=list)

    @property
    def total(self):
        return sum(line.amount for line in self.lines)

    def line(self, line_no):
        for line in self.lines:
            if line.line_no == line_no:
                return line
        return None


@dataclass
class Receipt:
    receipt_id: str
    po_id: str
    receipt_date: date
    received: dict = field(default_factory=dict)  # line_no -> qty diterima

    def qty_for(self, line_no):
        return self.received.get(line_no, 0)


@dataclass
class InvoiceLine:
    line_no: int
    item_name: str
    qty: int
    unit_price: int

    @property
    def amount(self):
        return self.qty * self.unit_price


@dataclass
class Invoice:
    invoice_id: str
    invoice_no: str
    vendor_id: str
    po_id: str  # boleh kosong bila invoice tanpa PO
    invoice_date: date
    lines: list = field(default_factory=list)

    @property
    def total(self):
        return sum(line.amount for line in self.lines)


@dataclass
class Dataset:
    vendors: dict = field(default_factory=dict)      # vendor_id -> Vendor
    pos: dict = field(default_factory=dict)          # po_id -> PO
    receipts: dict = field(default_factory=dict)     # po_id -> Receipt
    invoices: list = field(default_factory=list)     # list[Invoice]

    def invoices_sorted(self):
        return sorted(self.invoices, key=lambda inv: (inv.invoice_date, inv.invoice_id))


def load_vendors(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    vendors = {}
    for row in raw:
        vendor = Vendor(
            vendor_id=row["vendor_id"],
            name=row["name"],
            bank_name=row.get("bank_name", ""),
            bank_account=str(row.get("bank_account", "")),
            city=row.get("city", ""),
        )
        vendors[vendor.vendor_id] = vendor
    return vendors


def load_pos(path):
    pos = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            po_id = row["po_id"].strip()
            if po_id not in pos:
                pos[po_id] = PO(
                    po_id=po_id,
                    vendor_id=row["vendor_id"].strip(),
                    po_date=_parse_date(row["po_date"]),
                )
            pos[po_id].lines.append(
                POLine(
                    line_no=int(row["line_no"]),
                    item_name=row["item_name"].strip(),
                    unit=row.get("unit", "").strip(),
                    qty=int(row["qty"]),
                    unit_price=int(row["unit_price"]),
                )
            )
    for po in pos.values():
        po.lines.sort(key=lambda line: line.line_no)
    return pos


def load_receipts(path):
    receipts = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            po_id = row["po_id"].strip()
            if po_id not in receipts:
                receipts[po_id] = Receipt(
                    receipt_id=row["receipt_id"].strip(),
                    po_id=po_id,
                    receipt_date=_parse_date(row["receipt_date"]),
                )
            receipts[po_id].received[int(row["line_no"])] = int(row["qty_received"])
    return receipts


def load_invoices(path):
    invoices = {}
    order = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            invoice_id = row["invoice_id"].strip()
            if invoice_id not in invoices:
                invoices[invoice_id] = Invoice(
                    invoice_id=invoice_id,
                    invoice_no=row["invoice_no"].strip(),
                    vendor_id=row["vendor_id"].strip(),
                    po_id=(row.get("po_id") or "").strip(),
                    invoice_date=_parse_date(row["invoice_date"]),
                )
                order.append(invoice_id)
            invoices[invoice_id].lines.append(
                InvoiceLine(
                    line_no=int(row["line_no"]),
                    item_name=row["item_name"].strip(),
                    qty=int(row["qty"]),
                    unit_price=int(row["unit_price"]),
                )
            )
    result = [invoices[iid] for iid in order]
    for inv in result:
        inv.lines.sort(key=lambda line: line.line_no)
    return result


def load_dataset(samples_dir):
    samples = Path(samples_dir)
    return Dataset(
        vendors=load_vendors(samples / "vendors.json"),
        pos=load_pos(samples / "pos.csv"),
        receipts=load_receipts(samples / "receipts.csv"),
        invoices=load_invoices(samples / "invoices.csv"),
    )


def load_labels(samples_dir):
    path = Path(samples_dir) / "labels.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
