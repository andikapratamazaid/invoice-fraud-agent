"""Generator data sintetis berlabel untuk Invoice Fraud & Three-Way Match Agent.

Menghasilkan di folder samples:
- vendors.json  : 10 vendor fiktif, termasuk nomor rekening bank
- pos.csv       : 24 purchase order (satu baris per item)
- receipts.csv  : BAST penerimaan barang per PO (satu baris per item)
- invoices.csv  : kurang lebih 150 invoice, Januari s.d. Juni 2026
- labels.json   : label kebenaran per invoice_id (jenis fraud atau clean)

Fraud disuntikkan secara terkendali dengan seed tetap sehingga hasil
reproduksibel: ganda eksak, ganda samar, pecah invoice, tanpa PO,
kelebihan volume, selisih harga, pola angka bulat satu vendor, dan dua
vendor yang berbagi nomor rekening. Transaksi bersih mencakup kasus
batas yang sah: harga sedikit di bawah PO (dalam toleransi), satu dua
invoice bernominal bulat dari vendor biasa, dan invoice besar yang sah.
"""

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261107
BASE = Path(__file__).resolve().parent
SAMPLES = BASE / "samples"
START = date(2026, 1, 1)
END = date(2026, 6, 30)
APPROVAL_LIMIT = 50_000_000

VENDORS = [
    # vendor_id, nama, bank, rekening, kota
    ("V01", "PT Sumber Material Nusantara", "Bank Mandiri", "1370018452011", "Jakarta"),
    ("V02", "PT Baja Perkasa Abadi", "Bank BCA", "5260318874102", "Bekasi"),
    ("V03", "CV Karya Betonindo", "Bank BRI", "0382019927455", "Bogor"),
    ("V04", "PT Elektrikal Nusantara Jaya", "Bank BNI", "8801234567", "Jakarta"),
    ("V05", "CV Plumbing Sejahtera", "Bank Mandiri", "1370019923814", "Depok"),
    ("V06", "PT Cat Warna Prima", "Bank BCA", "5260317752098", "Tangerang"),
    ("V07", "PT Kayu Jati Makmur", "Bank BRI", "0382018817364", "Cikarang"),
    ("V08", "CV Alat Berat Rentindo", "Bank BNI", "0462017738291", "Jakarta"),
    ("V09", "PT Granit Alam Sejahtera", "Bank Mandiri", "1370016645207", "Tangerang"),
    ("V10", "PT Kaca Bangun Persada", "Bank BNI", "8801234567", "Jakarta"),
]

# kind: normal | partial_receipt | partial_billed | pecah | round
# lines: (item, unit, qty, harga satuan)
PO_DEFS = [
    ("PO-001", "V01", date(2026, 1, 5), "normal", 7, None,
     [("Semen Portland 50kg", "sak", 1200, 68500), ("Pasir beton", "m3", 180, 285000)]),
    ("PO-002", "V01", date(2026, 2, 2), "partial_receipt", 4, 0.70,
     [("Bata merah press", "pcs", 20000, 950), ("Semen Portland 50kg", "sak", 350, 68500)]),
    ("PO-003", "V01", date(2026, 3, 2), "partial_billed", 5, None,
     [("Pasir beton", "m3", 240, 285000), ("Semen Portland 50kg", "sak", 600, 68500)]),
    ("PO-004", "V02", date(2026, 1, 8), "normal", 7, None,
     [("Besi beton D13", "batang", 1500, 118500), ("Plat baja 6mm", "lembar", 260, 865000)]),
    ("PO-005", "V02", date(2026, 2, 9), "partial_receipt", 4, 0.65,
     [("Besi WF 200", "batang", 90, 1485000), ("Besi beton D13", "batang", 500, 118500)]),
    ("PO-006", "V02", date(2026, 3, 9), "partial_billed", 5, None,
     [("Besi beton D13", "batang", 700, 118500), ("Plat baja 6mm", "lembar", 80, 865000)]),
    ("PO-007", "V03", date(2026, 1, 5), "normal", 6, None,
     [("Beton ready mix K300", "m3", 420, 985000)]),
    ("PO-008", "V03", date(2026, 2, 20), "pecah", 7, None,
     [("Beton ready mix K300", "m3", 320, 985000)]),
    ("PO-009", "V03", date(2026, 4, 1), "normal", 6, None,
     [("Beton ready mix K225", "m3", 300, 885000)]),
    ("PO-010", "V04", date(2026, 1, 12), "normal", 7, None,
     [("Kabel NYM 3x2,5", "roll", 220, 685000), ("Panel listrik MDP", "unit", 26, 4750000)]),
    ("PO-011", "V04", date(2026, 3, 3), "normal", 5, None,
     [("Lampu LED highbay", "pcs", 900, 145500), ("Kabel NYM 3x2,5", "roll", 60, 685000)]),
    ("PO-012", "V05", date(2026, 1, 6), "partial_billed", 5, None,
     [("Pipa PVC 4 inch", "batang", 800, 92500), ("Fitting elbow 4 inch", "pcs", 2400, 18750)]),
    ("PO-013", "V05", date(2026, 2, 16), "partial_receipt", 4, 0.70,
     [("Pipa PVC 4 inch", "batang", 300, 92500), ("Kran air kuningan", "pcs", 200, 64500)]),
    ("PO-014", "V06", date(2026, 1, 14), "normal", 6, None,
     [("Cat tembok eksterior 25kg", "pail", 70, 685500), ("Thinner A", "liter", 350, 32500)]),
    ("PO-015", "V06", date(2026, 2, 23), "partial_billed", 5, None,
     [("Cat tembok eksterior 25kg", "pail", 120, 685500), ("Cat besi anti karat", "kaleng", 700, 88500)]),
    ("PO-016", "V07", date(2026, 1, 7), "normal", 6, None,
     [("Kayu kamper 5x7", "batang", 380, 145000), ("Plywood 9mm", "lembar", 550, 128500)]),
    ("PO-017", "V07", date(2026, 2, 24), "pecah", 6, None,
     [("Kayu kamper 5x7", "batang", 400, 145000), ("Plywood 9mm", "lembar", 600, 128500)]),
    ("PO-018", "V07", date(2026, 4, 6), "normal", 6, None,
     [("Plywood 9mm", "lembar", 220, 128500), ("Kayu kamper 5x7", "batang", 140, 145000)]),
    ("PO-019", "V08", date(2026, 1, 9), "partial_receipt", 4, 0.75,
     [("Sewa excavator PC200", "hari", 60, 2850000)]),
    ("PO-020", "V08", date(2026, 3, 11), "partial_billed", 5, None,
     [("Sewa crane 25 ton", "hari", 40, 4250000), ("Sewa genset 100 kVA", "hari", 50, 1950000)]),
    ("PO-021", "V09", date(2026, 1, 13), "round", 5, None,
     [("Granit tile 60x60", "m2", 1876, 250000)]),
    ("PO-022", "V09", date(2026, 3, 16), "round", 4, None,
     [("Granit tile 60x60", "m2", 1516, 250000)]),
    ("PO-023", "V10", date(2026, 1, 15), "normal", 7, None,
     [("Kaca tempered 10mm", "m2", 280, 785000), ("Rangka aluminium", "batang", 520, 342500)]),
    ("PO-024", "V10", date(2026, 3, 23), "partial_billed", 5, None,
     [("Kaca tempered 10mm", "m2", 120, 785000), ("Rangka aluminium", "batang", 200, 342500)]),
]

# Kelompok pecah invoice: qty per termin per line_no.
PECAH_PARTS = {
    "PO-008": {1: [20, 22, 19, 24, 80, 80, 75]},
    "PO-017": {1: [60, 70, 65, 70, 70, 65], 2: [90, 100, 95, 105, 105, 105]},
}
PECAH_GROUP_SIZE = {"PO-008": 4, "PO-017": 3}
# Termin granit V09 dirancang agar nominalnya bulat penuh, seluruhnya
# berkepala digit 9, sehingga distribusi digit pertamanya menyimpang
# ekstrem dari distribusi Benford.
ROUND_PARTS = {
    "PO-021": {1: [360, 368, 380, 392, 376]},
    "PO-022": {1: [364, 372, 384, 396]},
}
EKSAK_PO = ["PO-003", "PO-006", "PO-015"]          # sumber invoice ganda eksak
SAMAR_PO = ["PO-012", "PO-020", "PO-024"]          # sumber invoice ganda samar
SELISIH_PO = ["PO-003", "PO-012", "PO-015", "PO-024"]
KELEBIHAN_PO = ["PO-002", "PO-005", "PO-013", "PO-019"]
BILLED_FRACTION = 0.60  # porsi qty diterima yang ditagih pada PO partial_billed


def split_qty(total, k, rng):
    """Bagi total qty menjadi k bagian positif dengan proporsi bervariasi,
    menyerupai termin penagihan nyata yang tidak seragam."""
    if total <= 0:
        return [0] * k
    if total <= k:
        return [1] * total + [0] * (k - total)
    weights = [rng.uniform(0.3, 1.8) for _ in range(k)]
    weight_sum = sum(weights)
    parts = [max(1, int(total * w / weight_sum)) for w in weights]
    diff = total - sum(parts)
    i = 0
    while diff != 0 and i < 10000:
        idx = i % k
        if diff > 0:
            parts[idx] += 1
            diff -= 1
        elif parts[idx] > 1:
            parts[idx] -= 1
            diff += 1
        i += 1
    return parts


class InvoiceDraft:
    def __init__(self, vendor_id, po_id, inv_date, lines, label="clean",
                 number_mode="normal", number_ref=None):
        self.vendor_id = vendor_id
        self.po_id = po_id
        self.date = inv_date
        self.lines = lines  # list of (line_no, item, qty, unit_price)
        self.label = label
        self.number_mode = number_mode  # normal | copy | altered
        self.number_ref = number_ref    # draft sumber untuk mode copy/altered
        self.invoice_no = None
        self.invoice_id = None

    @property
    def total(self):
        return sum(qty * price for _, _, qty, price in self.lines)


def main():
    rng = random.Random(SEED)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    vendors = [
        {"vendor_id": vid, "name": name, "bank_name": bank, "bank_account": acc, "city": city}
        for vid, name, bank, acc, city in VENDORS
    ]

    po_rows, receipt_rows = [], []
    pos = {}
    for po_id, vendor_id, po_date, kind, n_term, frac, lines in PO_DEFS:
        receipt_date = po_date + timedelta(days=rng.randint(3, 9))
        received = {}
        for idx, (item, unit, qty, price) in enumerate(lines, start=1):
            po_rows.append({
                "po_id": po_id, "vendor_id": vendor_id, "po_date": po_date.isoformat(),
                "line_no": idx, "item_name": item, "unit": unit,
                "qty": qty, "unit_price": price,
            })
            rec_qty = qty if kind != "partial_receipt" else max(1, round(qty * frac))
            received[idx] = rec_qty
            receipt_rows.append({
                "receipt_id": f"BAST-{po_id.split('-')[1]}", "po_id": po_id,
                "receipt_date": receipt_date.isoformat(), "line_no": idx,
                "item_name": item, "qty_received": rec_qty,
            })
        pos[po_id] = {
            "vendor_id": vendor_id, "kind": kind, "n_term": n_term,
            "receipt_date": receipt_date, "received": received,
            "lines": {idx: (item, qty, price)
                      for idx, (item, unit, qty, price) in enumerate(lines, start=1)},
            "total": sum(qty * price for _, _, qty, price in lines),
        }

    # ---- susun termin (billing events) per PO ------------------------------
    events_by_vendor = {v[0]: [] for v in VENDORS}
    drafts = []
    po_events = {}
    for po_id, po in pos.items():
        vendor_id = po["vendor_id"]
        kind = po["kind"]
        n = po["n_term"]
        po_events[po_id] = []
        if kind == "pecah":
            parts_map = PECAH_PARTS[po_id]
            group_size = PECAH_GROUP_SIZE[po_id]
            for t in range(n):
                lines = []
                for line_no, (item, qty, price) in po["lines"].items():
                    q = parts_map[line_no][t]
                    if q > 0:
                        lines.append((line_no, item, q, price))
                gap = None
                if t < group_size:
                    gap = 10 if t == 0 else rng.choice([2, 3])
                ev = {"po_id": po_id, "vendor_id": vendor_id, "lines": lines,
                      "receipt_date": po["receipt_date"], "gap": gap, "termin": t,
                      "label": "pecah_invoice" if t < group_size else "clean"}
                po_events[po_id].append(ev)
        elif kind == "round":
            parts_map = ROUND_PARTS[po_id]
            for t in range(n):
                lines = []
                for line_no, (item, qty, price) in po["lines"].items():
                    q = parts_map[line_no][t]
                    if q > 0:
                        lines.append((line_no, item, q, price))
                ev = {"po_id": po_id, "vendor_id": vendor_id, "lines": lines,
                      "receipt_date": po["receipt_date"], "gap": None, "termin": t,
                      "label": "angka_bulat"}
                po_events[po_id].append(ev)
        else:
            bill_qty = {}
            for line_no in po["lines"]:
                received_qty = po["received"][line_no]
                if kind == "partial_billed":
                    target = max(n, int(received_qty * BILLED_FRACTION))
                else:
                    target = received_qty
                bill_qty[line_no] = split_qty(target, n, rng)
            for t in range(n):
                factor = rng.choice([1.0, 1.0, 0.998, 0.995])
                lines = []
                for line_no, (item, qty, price) in po["lines"].items():
                    q = bill_qty[line_no][t]
                    if q > 0:
                        lines.append((line_no, item, q, int(price * factor)))
                ev = {"po_id": po_id, "vendor_id": vendor_id, "lines": lines,
                      "receipt_date": po["receipt_date"], "gap": None, "termin": t}
                po_events[po_id].append(ev)
        events_by_vendor[vendor_id].extend(po_events[po_id])

    # Urutan PO per vendor mengikuti PO_DEFS agar jadwal deterministik.
    po_order = {po_id: i for i, (po_id, *_rest) in enumerate(PO_DEFS)}
    vendor_dates = {v[0]: [] for v in VENDORS}
    draft_by_event = {}
    for vendor_id, events in events_by_vendor.items():
        events.sort(key=lambda e: (po_order[e["po_id"]], e["termin"]))
        prev = None
        for ev in events:
            gap = ev["gap"] if ev["gap"] is not None else rng.randint(8, 11)
            earliest = ev["receipt_date"] + timedelta(days=1)
            if prev is None:
                inv_date = earliest + timedelta(days=rng.randint(0, 2))
            else:
                inv_date = max(earliest, prev + timedelta(days=gap))
            prev = inv_date
            draft = InvoiceDraft(vendor_id, ev["po_id"], inv_date, ev["lines"],
                                 label=ev.get("label", "clean"))
            drafts.append(draft)
            draft_by_event[id(ev)] = draft
            vendor_dates[vendor_id].append(inv_date)
            ev["draft"] = draft

    def vendor_totals(vendor_id):
        return {d.total for d in drafts if d.vendor_id == vendor_id}

    def register(draft):
        drafts.append(draft)
        vendor_dates[draft.vendor_id].append(draft.date)
        vendor_dates[draft.vendor_id].sort()

    # ---- suntikan fraud -----------------------------------------------------
    # Ganda eksak dan ganda samar: tiru termin kedua dari PO partial_billed.
    for po_id, mode, label in (
            [(p, "copy", "ganda_eksak") for p in EKSAK_PO] +
            [(p, "altered", "ganda_samar") for p in SAMAR_PO]):
        source = po_events[po_id][1]["draft"]
        clone = InvoiceDraft(source.vendor_id, po_id,
                             source.date + timedelta(days=rng.randint(2, 5)),
                             list(source.lines), label=label,
                             number_mode=mode, number_ref=source)
        source.label = label
        register(clone)

    # Kelebihan volume: tagih sisa qty PO yang tidak pernah diterima (BAST
    # parsial), setelah seluruh termin bersih selesai.
    for po_id in KELEBIHAN_PO:
        po = pos[po_id]
        lines = []
        for line_no, (item, qty, price) in po["lines"].items():
            shortfall = qty - po["received"][line_no]
            if shortfall > 0:
                lines.append((line_no, item, shortfall, price))
        last_date = max(ev["draft"].date for ev in po_events[po_id])
        kelebihan_date = last_date + timedelta(days=rng.randint(4, 7))
        if kelebihan_date > END:
            kelebihan_date = END
        draft = InvoiceDraft(po["vendor_id"], po_id,
                             kelebihan_date,
                             lines, label="kelebihan_volume")
        # jaga nominal unik per vendor agar tidak tertukar dengan ganda samar
        totals = vendor_totals(po["vendor_id"])
        while draft.total in totals:
            ln, item, q, price = draft.lines[0]
            draft.lines[0] = (ln, item, q + 1, price)
        register(draft)

    def extra_date(vendor_id):
        """Tanggal tambahan yang aman: dalam rentang 6 hari sebelum dan
        sesudah tanggal ini boleh ada paling banyak satu invoice lain dari
        vendor yang sama, sehingga invoice tambahan tidak pernah ikut
        membentuk kelompok 3 invoice dalam jendela 7 hari (pola pecah)."""
        dates = sorted(vendor_dates[vendor_id])

        def safe(cand):
            if cand in dates or not (START <= cand <= END):
                return False
            near = sum(1 for d in dates if abs((cand - d).days) <= 6)
            return near <= 1

        bases = list(dates)
        rng.shuffle(bases)
        for base in bases:
            for offset in (3, 4, 5, -3, -4, -5, 2, -2, 6, -6, 1, -1, 7, -7):
                cand = base + timedelta(days=offset)
                if safe(cand):
                    return cand
        start_offset = rng.randint(0, 170)
        for step in range(181):
            cand = START + timedelta(days=(start_offset + step) % 181)
            if safe(cand):
                return cand
        raise RuntimeError("tidak menemukan tanggal tambahan yang aman")

    # Selisih harga: tagihan kecil dari sisa qty belum tertagih pada PO
    # partial_billed, dengan harga satuan 5 s.d. 12 persen di atas PO.
    for po_id in SELISIH_PO:
        po = pos[po_id]
        line_no = 1
        item, qty, price = po["lines"][line_no]
        billed = sum(ev["draft"].lines[i][2] for ev in po_events[po_id]
                     for i in range(len(ev["draft"].lines))
                     if ev["draft"].lines[i][0] == line_no)
        headroom = po["received"][line_no] - billed
        q = max(2, min(headroom, int(qty * 0.05)))
        inflated = int(price * rng.choice([1.06, 1.08, 1.10, 1.12]))
        lines = [(line_no, item, q, inflated)]

        draft = InvoiceDraft(po["vendor_id"], po_id, extra_date(po["vendor_id"]),
                             lines, label="selisih_harga")
        totals = vendor_totals(po["vendor_id"])
        while draft.total in totals:
            ln, it, qq, pp = draft.lines[0]
            draft.lines[0] = (ln, it, qq + 1, pp)
        register(draft)

    # Tanpa PO: invoice berdiri sendiri pada tanggal yang terisolasi.
    tanpa_defs = [
        ("V04", [("Kabel NYM 3x2,5", "roll", 40, 685000)]),
        ("V05", [("Pipa PVC 4 inch", "batang", 210, 92500)]),
        ("V08", [("Sewa genset 100 kVA", "hari", 18, 1950000)]),
    ]
    for vendor_id, raw_lines in tanpa_defs:
        lines = [(1, item, qty, price) for item, unit, qty, price in raw_lines]
        cand = extra_date(vendor_id)
        draft = InvoiceDraft(vendor_id, "", cand, lines, label="tanpa_po")
        totals = vendor_totals(vendor_id)
        while draft.total in totals:
            ln, it, qq, pp = draft.lines[0]
            draft.lines[0] = (ln, it, qq + 1, pp)
        register(draft)

    # ---- perbaikan kecil pada invoice bersih -------------------------------
    # Jaga nominal unik per vendor (di luar pasangan ganda) dan batasi
    # nominal bulat penuh pada vendor selain V09.
    round_kept = 0
    for draft in drafts:
        if draft.vendor_id == "V09" or draft.label != "clean":
            continue
        if draft.total % 1_000_000 == 0:
            if round_kept < 2:
                round_kept += 1
            else:
                ln, it, qq, pp = max(draft.lines, key=lambda x: x[3])
                idx = draft.lines.index((ln, it, qq, pp))
                draft.lines[idx] = (ln, it, qq, pp - 137)
    seen_totals = {}
    for draft in drafts:
        if draft.label in ("ganda_eksak", "ganda_samar") or draft.vendor_id == "V09":
            continue
        totals = seen_totals.setdefault(draft.vendor_id, set())
        guard = 0
        while draft.total in totals and guard < 60:
            ln, it, qq, pp = max(draft.lines, key=lambda x: x[3])
            idx = draft.lines.index((ln, it, qq, pp))
            draft.lines[idx] = (ln, it, qq, pp - 251)
            guard += 1
        totals.add(draft.total)

    # ---- nomor invoice dan id ----------------------------------------------
    counters = {v[0]: 100 for v in VENDORS}
    for vendor_id in counters:
        own = sorted([d for d in drafts if d.vendor_id == vendor_id and d.number_mode == "normal"],
                     key=lambda d: d.date)
        for draft in own:
            counters[vendor_id] += 1
            draft.invoice_no = f"INV/2026/{counters[vendor_id]:04d}"
    for draft in drafts:
        if draft.number_mode == "copy":
            draft.invoice_no = draft.number_ref.invoice_no
        elif draft.number_mode == "altered":
            draft.invoice_no = draft.number_ref.invoice_no.replace("/0", "/", 1)

    drafts.sort(key=lambda d: (d.date, d.vendor_id, d.invoice_no))
    labels = {}
    invoice_rows = []
    for i, draft in enumerate(drafts, start=1):
        draft.invoice_id = f"F-{i:04d}"
        labels[draft.invoice_id] = draft.label
        for line_no, item, qty, price in draft.lines:
            invoice_rows.append({
                "invoice_id": draft.invoice_id, "invoice_no": draft.invoice_no,
                "vendor_id": draft.vendor_id, "po_id": draft.po_id,
                "invoice_date": draft.date.isoformat(), "line_no": line_no,
                "item_name": item, "qty": qty, "unit_price": price,
            })

    # ---- asersi invariant ----------------------------------------------------
    assert len(vendors) == 10
    assert len(pos) == 24
    assert 135 <= len(drafts) <= 165, len(drafts)
    billed_amount = {}
    for draft in drafts:
        if draft.po_id:
            billed_amount[draft.po_id] = billed_amount.get(draft.po_id, 0) + draft.total
    for po_id, amount in billed_amount.items():
        assert amount <= pos[po_id]["total"], (po_id, amount, pos[po_id]["total"])
    for draft in drafts:
        assert START <= draft.date <= END, draft.date
    from collections import Counter
    label_counts = Counter(labels.values())
    for label, minimum in [("ganda_eksak", 6), ("ganda_samar", 6), ("pecah_invoice", 7),
                           ("tanpa_po", 3), ("kelebihan_volume", 4), ("selisih_harga", 4),
                           ("angka_bulat", 9)]:
        assert label_counts[label] >= minimum, (label, label_counts[label])
    for vendor_id, *_ in VENDORS:
        if vendor_id == "V09":
            continue
        own = [d for d in drafts if d.vendor_id == vendor_id]
        round_ratio = sum(1 for d in own if d.total % 1_000_000 == 0) / len(own)
        assert round_ratio < 0.40, (vendor_id, round_ratio)

    # ---- tulis berkas ---------------------------------------------------------
    (SAMPLES / "vendors.json").write_text(
        json.dumps(vendors, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def write_csv(name, rows, fields):
        with open(SAMPLES / name, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write_csv("pos.csv", po_rows,
              ["po_id", "vendor_id", "po_date", "line_no", "item_name", "unit", "qty", "unit_price"])
    write_csv("receipts.csv", receipt_rows,
              ["receipt_id", "po_id", "receipt_date", "line_no", "item_name", "qty_received"])
    write_csv("invoices.csv", invoice_rows,
              ["invoice_id", "invoice_no", "vendor_id", "po_id", "invoice_date",
               "line_no", "item_name", "qty", "unit_price"])
    (SAMPLES / "labels.json").write_text(
        json.dumps(labels, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Vendor: {len(vendors)} | PO: {len(pos)} | Invoice: {len(drafts)}")
    print("Label:", dict(sorted(label_counts.items())))


if __name__ == "__main__":
    main()
