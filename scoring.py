"""Skor risiko per invoice dan per vendor.

Setiap jenis temuan memiliki bobot. Skor invoice adalah jumlah bobot
seluruh temuannya, dibatasi 100. Status ditentukan dari skor, kecuali
temuan keras yang langsung memaksa status TAHAN BAYAR.
"""

from collections import defaultdict

WEIGHTS = {
    "ganda_eksak": 70,
    "tanpa_po": 65,
    "kelebihan_volume": 60,
    "ganda_samar": 55,
    "pecah_invoice": 45,
    "melebihi_nilai_po": 40,
    "selisih_harga": 35,
    "angka_bulat": 10,
    "benford": 5,
    "rekening_sama": 0,  # level vendor, masuk ke skor vendor bukan skor invoice
}

HARD_TYPES = {"ganda_eksak", "tanpa_po", "kelebihan_volume"}

CHECK_LABELS = {
    "ganda_eksak": "Invoice ganda eksak",
    "tanpa_po": "Invoice tanpa PO",
    "kelebihan_volume": "Kelebihan volume tagih",
    "ganda_samar": "Invoice ganda samar",
    "pecah_invoice": "Pecah invoice hindari persetujuan",
    "melebihi_nilai_po": "Kumulatif melebihi nilai PO",
    "selisih_harga": "Selisih harga di atas toleransi",
    "angka_bulat": "Pola nominal bulat berulang",
    "benford": "Catatan uji Benford",
    "rekening_sama": "Rekening bank dipakai bersama",
}

SHARED_ACCOUNT_VENDOR_BONUS = 15


def status_for_score(score, has_hard=False):
    if has_hard or score >= 60:
        return "TAHAN BAYAR"
    if score >= 30:
        return "PERINGATAN"
    return "BERSIH"


class InvoiceScore:
    def __init__(self, invoice, findings):
        self.invoice = invoice
        self.findings = findings
        self.score = min(100, sum(WEIGHTS.get(f.check_type, 0) for f in findings))
        self.has_hard = any(f.check_type in HARD_TYPES for f in findings)
        self.status = status_for_score(self.score, self.has_hard)


def score_invoices(dataset, analysis):
    scores = {}
    for inv in dataset.invoices:
        scores[inv.invoice_id] = InvoiceScore(inv, analysis.findings_for_invoice(inv.invoice_id))
    return scores


def vendor_risk(dataset, analysis, scores):
    """Rekap risiko per vendor, diurutkan dari risiko tertinggi.

    Skor vendor = 60% rata-rata skor invoice + 40% skor invoice maksimum,
    ditambah bonus 15 bila vendor berbagi rekening dengan vendor lain,
    dibatasi 100.
    """
    shared_vendor_ids = set()
    for account, vendors in analysis.shared_accounts:
        for vendor in vendors:
            shared_vendor_ids.add(vendor.vendor_id)
    by_vendor = defaultdict(list)
    for inv in dataset.invoices:
        by_vendor[inv.vendor_id].append(scores[inv.invoice_id])
    findings_by_vendor = defaultdict(int)
    hard_by_vendor = defaultdict(int)
    for finding in analysis.findings:
        if finding.invoice_id is not None:
            findings_by_vendor[finding.vendor_id] += 1
            if finding.check_type in HARD_TYPES:
                hard_by_vendor[finding.vendor_id] += 1
    rows = []
    for vendor_id, vendor in dataset.vendors.items():
        inv_scores = by_vendor.get(vendor_id, [])
        if inv_scores:
            avg = sum(s.score for s in inv_scores) / len(inv_scores)
            mx = max(s.score for s in inv_scores)
        else:
            avg, mx = 0.0, 0
        risk = int(round(0.6 * avg + 0.4 * mx))
        if vendor_id in shared_vendor_ids:
            risk += SHARED_ACCOUNT_VENDOR_BONUS
        risk = min(100, risk)
        status_counts = defaultdict(int)
        for s in inv_scores:
            status_counts[s.status] += 1
        rows.append({
            "vendor_id": vendor_id,
            "name": vendor.name,
            "risk": risk,
            "invoice_count": len(inv_scores),
            "total_amount": sum(s.invoice.total for s in inv_scores),
            "findings": findings_by_vendor.get(vendor_id, 0),
            "hard_findings": hard_by_vendor.get(vendor_id, 0),
            "tahan_bayar": status_counts.get("TAHAN BAYAR", 0),
            "peringatan": status_counts.get("PERINGATAN", 0),
            "bersih": status_counts.get("BERSIH", 0),
            "shared_account": vendor_id in shared_vendor_ids,
        })
    rows.sort(key=lambda r: (-r["risk"], r["vendor_id"]))
    return rows
