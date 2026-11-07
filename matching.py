"""Mesin pencocokan three-way: PO vs BAST (penerimaan) vs invoice.

Untuk setiap invoice, modul ini menautkan invoice ke PO dan BAST-nya,
lalu menyusun perbandingan per item: jumlah dan harga menurut PO,
jumlah yang benar-benar diterima menurut BAST, dan jumlah yang ditagih
pada invoice ini maupun kumulatif seluruh invoice untuk PO tersebut.
"""

from dataclasses import dataclass, field


@dataclass
class LineMatch:
    line_no: int
    item_name: str
    po_qty: int = 0
    po_price: int = 0
    received_qty: int = 0
    billed_qty: int = 0        # qty pada invoice yang sedang diperiksa
    billed_price: int = 0      # harga satuan pada invoice ini
    cum_billed_qty: int = 0    # kumulatif qty tertagih sampai invoice ini
    cum_billed_before: int = 0


@dataclass
class MatchResult:
    invoice: object
    po: object = None
    receipt: object = None
    lines: list = field(default_factory=list)
    cum_amount_before: int = 0   # kumulatif nominal tertagih sebelum invoice ini
    cum_amount_after: int = 0    # kumulatif nominal termasuk invoice ini


def build_cumulative(dataset):
    """Hitung kumulatif qty per (po_id, line_no) dan nominal per po_id
    mengikuti urutan tanggal invoice. Mengembalikan dict invoice_id ->
    (cum_qty_dict, cum_amount_before, cum_amount_after)."""
    cum_qty = {}
    cum_amount = {}
    per_invoice = {}
    for inv in dataset.invoices_sorted():
        if not inv.po_id or inv.po_id not in dataset.pos:
            per_invoice[inv.invoice_id] = ({}, cum_amount.get(inv.po_id, 0), cum_amount.get(inv.po_id, 0))
            continue
        before_amount = cum_amount.get(inv.po_id, 0)
        snapshot = {}
        for line in inv.lines:
            key = (inv.po_id, line.line_no)
            before = cum_qty.get(key, 0)
            snapshot[line.line_no] = (before, before + line.qty)
            cum_qty[key] = before + line.qty
        after_amount = before_amount + inv.total
        cum_amount[inv.po_id] = after_amount
        per_invoice[inv.invoice_id] = (snapshot, before_amount, after_amount)
    return per_invoice


def match_invoice(invoice, dataset, cumulative=None):
    """Susun MatchResult untuk satu invoice."""
    if cumulative is None:
        cumulative = build_cumulative(dataset)
    po = dataset.pos.get(invoice.po_id) if invoice.po_id else None
    receipt = dataset.receipts.get(invoice.po_id) if invoice.po_id else None
    snapshot, before_amount, after_amount = cumulative.get(invoice.invoice_id, ({}, 0, 0))
    result = MatchResult(
        invoice=invoice,
        po=po,
        receipt=receipt,
        cum_amount_before=before_amount,
        cum_amount_after=after_amount,
    )
    if po is None:
        for line in invoice.lines:
            result.lines.append(
                LineMatch(
                    line_no=line.line_no,
                    item_name=line.item_name,
                    billed_qty=line.qty,
                    billed_price=line.unit_price,
                )
            )
        return result
    seen = set()
    for line in invoice.lines:
        po_line = po.line(line.line_no)
        before, after = snapshot.get(line.line_no, (0, line.qty))
        result.lines.append(
            LineMatch(
                line_no=line.line_no,
                item_name=line.item_name,
                po_qty=po_line.qty if po_line else 0,
                po_price=po_line.unit_price if po_line else 0,
                received_qty=receipt.qty_for(line.line_no) if receipt else 0,
                billed_qty=line.qty,
                billed_price=line.unit_price,
                cum_billed_qty=after,
                cum_billed_before=before,
            )
        )
        seen.add(line.line_no)
    return result


def match_all(dataset):
    cumulative = build_cumulative(dataset)
    return {inv.invoice_id: match_invoice(inv, dataset, cumulative) for inv in dataset.invoices}
