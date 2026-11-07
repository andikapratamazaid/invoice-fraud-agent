"""Sembilan pemeriksaan fraud dan selisih dokumen, plus satu pemeriksaan
level vendor (rekening bank yang sama dipakai beberapa vendor).

Semua pemeriksaan deterministik: aturan yang sama atas data yang sama
selalu menghasilkan temuan yang sama.
"""

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

import matching

APPROVAL_LIMIT = 50_000_000       # batas persetujuan pembayaran (Rp)
PRICE_TOLERANCE = 0.01            # toleransi selisih harga 1 persen
SPLIT_WINDOW_DAYS = 7             # jendela deteksi pecah invoice
SPLIT_MIN_COUNT = 3               # minimal invoice dalam satu kelompok pecah
FUZZY_MAX_DAYS = 14               # jarak tanggal maksimum ganda samar
ROUND_UNIT = 1_000_000            # nominal bulat penuh: kelipatan Rp1.000.000
ROUND_MIN_INVOICES = 5            # minimal invoice agar pola bulat dinilai
ROUND_MIN_RATIO = 0.40            # proporsi minimal nominal bulat per vendor
BENFORD_BIG_INVOICE = 50_000_000  # ambang invoice besar untuk catatan Benford
BENFORD_MAD_LIMIT = 0.010         # batas MAD Nigrini digit pertama (dataset)
# Untuk sampel per vendor yang kecil (di bawah 30 invoice), MAD Nigrini
# standar terlalu sensitif terhadap fluktuasi acak, jadi dipakai ambang
# penyimpangan ekstrem agar hanya pola yang benar-benar menyimpang yang
# ditandai.
BENFORD_VENDOR_MAD_LIMIT = 0.15


@dataclass
class Finding:
    check_type: str
    vendor_id: str
    detail: str
    invoice_id: str = None  # None berarti temuan level vendor


# ---------------------------------------------------------------- utilitas

def normalize_invoice_no(invoice_no):
    """Ambil hanya digit dari nomor invoice untuk perbandingan."""
    return re.sub(r"\D", "", invoice_no or "")


def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[len(b)]


def first_digit(amount):
    amount = abs(int(amount))
    if amount == 0:
        return 0
    while amount >= 10:
        amount //= 10
    return amount


def benford_stats(amounts):
    """Statistik kesesuaian Benford untuk digit pertama.

    Mengembalikan dict berisi jumlah data, proporsi aktual per digit,
    proporsi harapan Benford, chi-square, dan MAD (mean absolute deviation)
    mengikuti kriteria Nigrini.
    """
    amounts = [a for a in amounts if a and a > 0]
    n = len(amounts)
    expected = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
    counts = {d: 0 for d in range(1, 10)}
    for amount in amounts:
        d = first_digit(amount)
        if d in counts:
            counts[d] += 1
    actual = {d: (counts[d] / n if n else 0.0) for d in range(1, 10)}
    chi2 = 0.0
    if n:
        chi2 = sum((counts[d] - n * expected[d]) ** 2 / (n * expected[d]) for d in range(1, 10))
    mad = sum(abs(actual[d] - expected[d]) for d in range(1, 10)) / 9 if n else 0.0
    if mad <= 0.006:
        conformity = "sesuai (close conformity)"
    elif mad <= 0.008:
        conformity = "cukup sesuai (acceptable conformity)"
    elif mad <= BENFORD_MAD_LIMIT:
        conformity = "marjinal (marginally acceptable)"
    else:
        conformity = "tidak sesuai (nonconformity)"
    return {
        "n": n,
        "counts": counts,
        "actual": actual,
        "expected": expected,
        "chi_square": chi2,
        "mad": mad,
        "conformity": conformity,
        "conforming": mad <= BENFORD_MAD_LIMIT,
    }


def is_round_amount(amount):
    return amount > 0 and amount % ROUND_UNIT == 0


# ---------------------------------------------------------------- pemeriksaan

def check_tanpa_po(dataset):
    findings = []
    for inv in dataset.invoices:
        if not inv.po_id:
            findings.append(Finding("tanpa_po", inv.vendor_id,
                                    "Invoice tidak mencantumkan referensi PO.",
                                    inv.invoice_id))
        elif inv.po_id not in dataset.pos:
            findings.append(Finding("tanpa_po", inv.vendor_id,
                                    f"Referensi PO {inv.po_id} tidak ditemukan pada data PO.",
                                    inv.invoice_id))
    return findings


def check_selisih_harga(matches):
    findings = []
    for inv_id, match in matches.items():
        if match.po is None:
            continue
        for line in match.lines:
            if line.po_price <= 0:
                continue
            diff = (line.billed_price - line.po_price) / line.po_price
            if diff > PRICE_TOLERANCE:
                findings.append(Finding(
                    "selisih_harga", match.invoice.vendor_id,
                    f"Item {line.item_name}: harga invoice Rp{line.billed_price:,} "
                    f"lebih tinggi {diff * 100:.1f}% dari harga PO Rp{line.po_price:,}.",
                    inv_id))
                break  # satu temuan per invoice sudah cukup untuk skor
    return findings


def check_kelebihan_volume(matches):
    findings = []
    for inv_id, match in matches.items():
        if match.po is None:
            continue
        for line in match.lines:
            over_single = line.billed_qty > line.received_qty and line.received_qty >= 0
            over_cum = line.cum_billed_qty > line.received_qty and line.billed_qty > 0
            if match.receipt is not None and (over_single or over_cum):
                findings.append(Finding(
                    "kelebihan_volume", match.invoice.vendor_id,
                    f"Item {line.item_name}: kumulatif ditagih {line.cum_billed_qty} "
                    f"melebihi jumlah diterima pada BAST {line.received_qty}.",
                    inv_id))
                break
    return findings


def check_melebihi_nilai_po(matches):
    findings = []
    for inv_id, match in matches.items():
        if match.po is None:
            continue
        if match.cum_amount_after > match.po.total and match.invoice.total > 0:
            findings.append(Finding(
                "melebihi_nilai_po", match.invoice.vendor_id,
                f"Kumulatif tagihan Rp{match.cum_amount_after:,} melebihi nilai PO "
                f"{match.po.po_id} sebesar Rp{match.po.total:,}.",
                inv_id))
    return findings


def check_ganda_eksak(dataset):
    findings = []
    groups = defaultdict(list)
    for inv in dataset.invoices:
        key = (inv.vendor_id, normalize_invoice_no(inv.invoice_no))
        if key[1]:
            groups[key].append(inv)
    for (vendor_id, digits), invs in groups.items():
        if len(invs) > 1:
            for inv in invs:
                findings.append(Finding(
                    "ganda_eksak", vendor_id,
                    f"Nomor invoice {inv.invoice_no} muncul {len(invs)} kali untuk vendor yang sama.",
                    inv.invoice_id))
    return findings


def check_ganda_samar(dataset):
    findings = []
    by_vendor = defaultdict(list)
    for inv in dataset.invoices_sorted():
        by_vendor[inv.vendor_id].append(inv)
    flagged = set()
    for vendor_id, invs in by_vendor.items():
        for i in range(len(invs)):
            for j in range(i + 1, len(invs)):
                a, b = invs[i], invs[j]
                da, db = normalize_invoice_no(a.invoice_no), normalize_invoice_no(b.invoice_no)
                if not da or da == db:
                    continue
                if a.total != b.total:
                    continue
                if abs((a.invoice_date - b.invoice_date).days) > FUZZY_MAX_DAYS:
                    continue
                if levenshtein(da, db) <= 1:
                    for inv in (a, b):
                        if inv.invoice_id not in flagged:
                            flagged.add(inv.invoice_id)
                            findings.append(Finding(
                                "ganda_samar", vendor_id,
                                f"Nomor invoice {a.invoice_no} dan {b.invoice_no} berbeda tipis, "
                                f"nominal sama Rp{a.total:,}, tanggal berdekatan.",
                                inv.invoice_id))
    return findings


def check_pecah_invoice(dataset):
    findings = []
    by_vendor = defaultdict(list)
    for inv in dataset.invoices_sorted():
        by_vendor[inv.vendor_id].append(inv)
    for vendor_id, invs in by_vendor.items():
        flagged = set()
        n = len(invs)
        for start in range(n):
            window = []
            for k in range(start, n):
                delta = (invs[k].invoice_date - invs[start].invoice_date).days
                if delta >= SPLIT_WINDOW_DAYS:
                    break
                window.append(invs[k])
            if len(window) >= SPLIT_MIN_COUNT:
                if all(inv.total < APPROVAL_LIMIT for inv in window) and \
                        sum(inv.total for inv in window) > APPROVAL_LIMIT:
                    for inv in window:
                        flagged.add(inv.invoice_id)
        for inv in invs:
            if inv.invoice_id in flagged:
                findings.append(Finding(
                    "pecah_invoice", vendor_id,
                    f"Bagian dari kelompok {len(flagged)} invoice dalam {SPLIT_WINDOW_DAYS} hari, "
                    f"masing-masing di bawah batas persetujuan Rp{APPROVAL_LIMIT:,}, "
                    f"total kelompok melebihi batas itu.",
                    inv.invoice_id))
    return findings


def check_angka_bulat(dataset):
    """Pola level vendor: proporsi nominal bulat penuh terlalu tinggi.
    Invoice dengan nominal bulat dari vendor yang tertandai ikut ditandai."""
    findings = []
    flagged_vendors = {}
    by_vendor = defaultdict(list)
    for inv in dataset.invoices:
        by_vendor[inv.vendor_id].append(inv)
    for vendor_id, invs in by_vendor.items():
        if len(invs) < ROUND_MIN_INVOICES:
            continue
        round_invs = [inv for inv in invs if is_round_amount(inv.total)]
        ratio = len(round_invs) / len(invs)
        if ratio >= ROUND_MIN_RATIO:
            flagged_vendors[vendor_id] = (len(round_invs), len(invs), ratio)
            for inv in round_invs:
                findings.append(Finding(
                    "angka_bulat", vendor_id,
                    f"Nominal bulat penuh Rp{inv.total:,}; vendor ini memiliki "
                    f"{len(round_invs)} dari {len(invs)} invoice bernominal bulat "
                    f"({ratio * 100:.0f}%).",
                    inv.invoice_id))
    return findings, flagged_vendors


def check_benford(dataset):
    """Uji Benford level dataset dan per vendor. Invoice besar dari vendor
    yang distribusinya tidak sesuai diberi catatan ringan."""
    findings = []
    all_amounts = [inv.total for inv in dataset.invoices]
    dataset_stats = benford_stats(all_amounts)
    by_vendor = defaultdict(list)
    for inv in dataset.invoices:
        by_vendor[inv.vendor_id].append(inv)
    vendor_stats = {}
    for vendor_id, invs in by_vendor.items():
        stats = benford_stats([inv.total for inv in invs])
        vendor_stats[vendor_id] = stats
        if len(invs) >= 8 and stats["mad"] > BENFORD_VENDOR_MAD_LIMIT:
            for inv in invs:
                if inv.total >= BENFORD_BIG_INVOICE:
                    findings.append(Finding(
                        "benford", vendor_id,
                        f"Invoice besar Rp{inv.total:,} dari vendor yang distribusi digit "
                        f"pertamanya tidak sesuai Benford (MAD {stats['mad']:.4f}).",
                        inv.invoice_id))
    return findings, dataset_stats, vendor_stats


def check_rekening_sama(dataset):
    findings = []
    by_account = defaultdict(list)
    for vendor in dataset.vendors.values():
        if vendor.bank_account:
            by_account[vendor.bank_account].append(vendor)
    groups = []
    for account, vendors in by_account.items():
        if len(vendors) > 1:
            groups.append((account, vendors))
            names = ", ".join(v.name for v in vendors)
            for vendor in vendors:
                findings.append(Finding(
                    "rekening_sama", vendor.vendor_id,
                    f"Nomor rekening {account} di {vendor.bank_name} dipakai bersama oleh: {names}.",
                    None))
    return findings, groups


@dataclass
class AnalysisResult:
    findings: list = field(default_factory=list)
    matches: dict = field(default_factory=dict)
    benford_dataset: dict = field(default_factory=dict)
    benford_vendors: dict = field(default_factory=dict)
    round_vendors: dict = field(default_factory=dict)
    shared_accounts: list = field(default_factory=list)

    def findings_for_invoice(self, invoice_id):
        return [f for f in self.findings if f.invoice_id == invoice_id]

    def findings_by_type(self):
        grouped = defaultdict(list)
        for finding in self.findings:
            grouped[finding.check_type].append(finding)
        return grouped


def run_checks(dataset):
    matches = matching.match_all(dataset)
    findings = []
    findings += check_tanpa_po(dataset)
    findings += check_selisih_harga(matches)
    findings += check_kelebihan_volume(matches)
    findings += check_melebihi_nilai_po(matches)
    findings += check_ganda_eksak(dataset)
    findings += check_ganda_samar(dataset)
    findings += check_pecah_invoice(dataset)
    round_findings, round_vendors = check_angka_bulat(dataset)
    findings += round_findings
    benford_findings, ds_stats, vendor_stats = check_benford(dataset)
    findings += benford_findings
    account_findings, groups = check_rekening_sama(dataset)
    findings += account_findings
    return AnalysisResult(
        findings=findings,
        matches=matches,
        benford_dataset=ds_stats,
        benford_vendors=vendor_stats,
        round_vendors=round_vendors,
        shared_accounts=groups,
    )
