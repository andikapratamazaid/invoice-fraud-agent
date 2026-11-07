from datetime import date, timedelta

import checks
import matching
from conftest import make_dataset, make_invoice, make_po, make_receipt, make_vendor

D = date


def _base_dataset(invoice_lines_list, po_qty=100, po_price=100_000, received=100):
    po = make_po("PO-1", "V1", [("Item A", po_qty, po_price)])
    receipt = make_receipt(po, {1: received})
    invoices = [make_invoice(f"I{i+1}", "V1", "PO-1", inv_date, lines)
                for i, (inv_date, lines) in enumerate(invoice_lines_list)]
    return make_dataset([make_vendor("V1")], [po], [receipt], invoices)


def test_selisih_harga_di_atas_toleransi():
    ds = _base_dataset([(D(2026, 1, 10), [(1, "Item A", 10, 105_000)])])
    findings = checks.check_selisih_harga(matching.match_all(ds))
    assert [f.invoice_id for f in findings] == ["I1"]


def test_selisih_harga_dalam_toleransi_aman():
    ds = _base_dataset([(D(2026, 1, 10), [(1, "Item A", 10, 100_500)])])
    assert checks.check_selisih_harga(matching.match_all(ds)) == []


def test_selisih_harga_lebih_murah_aman():
    ds = _base_dataset([(D(2026, 1, 10), [(1, "Item A", 10, 90_000)])])
    assert checks.check_selisih_harga(matching.match_all(ds)) == []


def test_kelebihan_volume_kumulatif():
    ds = _base_dataset(
        [(D(2026, 1, 10), [(1, "Item A", 70, 100_000)]),
         (D(2026, 1, 20), [(1, "Item A", 30, 100_000)])],
        received=70)
    findings = checks.check_kelebihan_volume(matching.match_all(ds))
    assert [f.invoice_id for f in findings] == ["I2"]


def test_kelebihan_volume_sebagian_normal_aman():
    ds = _base_dataset(
        [(D(2026, 1, 10), [(1, "Item A", 40, 100_000)]),
         (D(2026, 1, 20), [(1, "Item A", 30, 100_000)])],
        received=70)
    assert checks.check_kelebihan_volume(matching.match_all(ds)) == []


def test_melebihi_nilai_po():
    ds = _base_dataset(
        [(D(2026, 1, 10), [(1, "Item A", 60, 1_000_000)]),
         (D(2026, 1, 20), [(1, "Item A", 50, 1_000_000)])],
        po_qty=100, po_price=1_000_000, received=200)
    findings = checks.check_melebihi_nilai_po(matching.match_all(ds))
    assert [f.invoice_id for f in findings] == ["I2"]


def test_tanpa_po_kosong_dan_ngawur():
    po = make_po("PO-1", "V1", [("Item A", 10, 1000)])
    inv1 = make_invoice("I1", "V1", "", D(2026, 2, 1), [(1, "Item A", 1, 1000)])
    inv2 = make_invoice("I2", "V1", "PO-XXX", D(2026, 2, 2), [(1, "Item A", 1, 1000)])
    inv3 = make_invoice("I3", "V1", "PO-1", D(2026, 2, 3), [(1, "Item A", 1, 1000)])
    ds = make_dataset([make_vendor("V1")], [po], [make_receipt(po, {1: 10})],
                      [inv1, inv2, inv3])
    findings = checks.check_tanpa_po(ds)
    assert sorted(f.invoice_id for f in findings) == ["I1", "I2"]


def test_ganda_eksak():
    inv1 = make_invoice("I1", "V1", "", D(2026, 2, 1), [(1, "A", 2, 5000)], invoice_no="INV/2026/0101")
    inv2 = make_invoice("I2", "V1", "", D(2026, 2, 4), [(1, "A", 2, 5000)], invoice_no="INV/2026/0101")
    inv3 = make_invoice("I3", "V1", "", D(2026, 2, 9), [(1, "A", 2, 5000)], invoice_no="INV/2026/0102")
    inv4 = make_invoice("I4", "V2", "", D(2026, 2, 4), [(1, "A", 2, 5000)], invoice_no="INV/2026/0101")
    ds = make_dataset([make_vendor("V1"), make_vendor("V2", "222")], [], [],
                      [inv1, inv2, inv3, inv4])
    findings = checks.check_ganda_eksak(ds)
    assert sorted(f.invoice_id for f in findings) == ["I1", "I2"]


def test_ganda_samar_positif():
    inv1 = make_invoice("I1", "V1", "", D(2026, 2, 1), [(1, "A", 2, 5000)], invoice_no="INV/2026/0107")
    inv2 = make_invoice("I2", "V1", "", D(2026, 2, 5), [(1, "A", 2, 5000)], invoice_no="INV/2026/107")
    ds = make_dataset([make_vendor("V1")], [], [], [inv1, inv2])
    findings = checks.check_ganda_samar(ds)
    assert sorted(f.invoice_id for f in findings) == ["I1", "I2"]


def test_ganda_samar_nominal_beda_aman():
    inv1 = make_invoice("I1", "V1", "", D(2026, 2, 1), [(1, "A", 2, 5000)], invoice_no="INV/2026/0107")
    inv2 = make_invoice("I2", "V1", "", D(2026, 2, 5), [(1, "A", 3, 5000)], invoice_no="INV/2026/107")
    ds = make_dataset([make_vendor("V1")], [], [], [inv1, inv2])
    assert checks.check_ganda_samar(ds) == []


def test_ganda_samar_tanggal_jauh_aman():
    inv1 = make_invoice("I1", "V1", "", D(2026, 2, 1), [(1, "A", 2, 5000)], invoice_no="INV/2026/0107")
    inv2 = make_invoice("I2", "V1", "", D(2026, 3, 5), [(1, "A", 2, 5000)], invoice_no="INV/2026/107")
    ds = make_dataset([make_vendor("V1")], [], [], [inv1, inv2])
    assert checks.check_ganda_samar(ds) == []


def _pecah_dataset(dates_amounts):
    invs = [make_invoice(f"I{i+1}", "V1", "", d, [(1, "A", 1, amount)])
            for i, (d, amount) in enumerate(dates_amounts)]
    return make_dataset([make_vendor("V1")], [], [], invs)


def test_pecah_invoice_positif():
    ds = _pecah_dataset([(D(2026, 3, 1), 20_000_000), (D(2026, 3, 3), 22_000_000),
                         (D(2026, 3, 6), 19_000_000)])
    findings = checks.check_pecah_invoice(ds)
    assert sorted(f.invoice_id for f in findings) == ["I1", "I2", "I3"]


def test_pecah_invoice_berjauhan_aman():
    ds = _pecah_dataset([(D(2026, 3, 1), 20_000_000), (D(2026, 3, 11), 22_000_000),
                         (D(2026, 3, 21), 19_000_000)])
    assert checks.check_pecah_invoice(ds) == []


def test_pecah_invoice_satu_besar_aman():
    ds = _pecah_dataset([(D(2026, 3, 1), 20_000_000), (D(2026, 3, 3), 60_000_000),
                         (D(2026, 3, 5), 19_000_000)])
    assert checks.check_pecah_invoice(ds) == []


def test_pecah_invoice_total_kecil_aman():
    ds = _pecah_dataset([(D(2026, 3, 1), 10_000_000), (D(2026, 3, 3), 12_000_000),
                         (D(2026, 3, 5), 11_000_000)])
    assert checks.check_pecah_invoice(ds) == []


def test_angka_bulat_vendor_terflag():
    amounts = [5_000_000, 12_000_000, 8_000_000, 20_000_000, 7_000_000]
    invs = [make_invoice(f"I{i+1}", "V1", "", D(2026, 1, 5) + timedelta(days=i * 12), [(1, "A", 1, a)])
            for i, a in enumerate(amounts)]
    ds = make_dataset([make_vendor("V1")], [], [], invs)
    findings, flagged = checks.check_angka_bulat(ds)
    assert "V1" in flagged
    assert len(findings) == 5


def test_angka_bulat_proporsi_rendah_aman():
    amounts = [5_100_000, 12_000_000, 8_300_000, 20_700_000, 7_900_000]
    invs = [make_invoice(f"I{i+1}", "V1", "", D(2026, 1, 5) + timedelta(days=i * 12), [(1, "A", 1, a)])
            for i, a in enumerate(amounts)]
    ds = make_dataset([make_vendor("V1")], [], [], invs)
    findings, flagged = checks.check_angka_bulat(ds)
    assert findings == [] and flagged == {}


def test_benford_sesuai_dan_menyimpang():
    counts = {1: 301, 2: 176, 3: 125, 4: 97, 5: 79, 6: 67, 7: 58, 8: 51, 9: 46}
    amounts = []
    for digit, count in counts.items():
        for j in range(count):
            amounts.append(digit * (10 ** (j % 4)))
    stats = checks.benford_stats(amounts)
    assert stats["conforming"] is True
    skewed = checks.benford_stats([9 * (10 ** (j % 3)) for j in range(200)])
    assert skewed["conforming"] is False
    assert skewed["mad"] > 0.15


def test_rekening_sama():
    v1 = make_vendor("V1", account="999")
    v2 = make_vendor("V2", account="999")
    v3 = make_vendor("V3", account="888")
    ds = make_dataset([v1, v2, v3], [], [], [])
    findings, groups = checks.check_rekening_sama(ds)
    assert len(groups) == 1
    assert sorted(f.vendor_id for f in findings) == ["V1", "V2"]
    assert all(f.invoice_id is None for f in findings)


def test_levenshtein_dan_normalisasi():
    assert checks.normalize_invoice_no("INV/2026/0107") == "20260107"
    assert checks.levenshtein("20260107", "2026107") == 1
    assert checks.levenshtein("abc", "abc") == 0
    assert checks.levenshtein("abc", "xyz") == 3
