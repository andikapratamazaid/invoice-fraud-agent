import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loader import Dataset, Invoice, InvoiceLine, PO, POLine, Receipt, Vendor


def make_vendor(vid, account="111"):
    return Vendor(vendor_id=vid, name=f"Vendor {vid}", bank_name="Bank Uji",
                  bank_account=account, city="Jakarta")


def make_po(po_id, vendor_id, lines):
    po = PO(po_id=po_id, vendor_id=vendor_id, po_date=date(2026, 1, 5))
    po.lines = [POLine(line_no=i + 1, item_name=item, unit="unit", qty=qty, unit_price=price)
                for i, (item, qty, price) in enumerate(lines)]
    return po


def make_receipt(po, received):
    receipt = Receipt(receipt_id=f"BAST-{po.po_id}", po_id=po.po_id,
                      receipt_date=date(2026, 1, 8))
    receipt.received = dict(received)
    return receipt


def make_invoice(invoice_id, vendor_id, po_id, inv_date, lines, invoice_no=None):
    inv = Invoice(invoice_id=invoice_id,
                  invoice_no=invoice_no or f"INV/2026/{invoice_id}",
                  vendor_id=vendor_id, po_id=po_id, invoice_date=inv_date)
    inv.lines = [InvoiceLine(line_no=ln, item_name=item, qty=qty, unit_price=price)
                 for ln, item, qty, price in lines]
    return inv


def make_dataset(vendors, pos, receipts, invoices):
    return Dataset(
        vendors={v.vendor_id: v for v in vendors},
        pos={p.po_id: p for p in pos},
        receipts={r.po_id: r for r in receipts},
        invoices=invoices,
    )
